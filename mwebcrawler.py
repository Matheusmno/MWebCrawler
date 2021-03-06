#  -*- coding: utf-8 -*-
#    @package: mwebcrawler.py
#     @author: Guilherme N. Ramos (gnramos@unb.br)
#
# Funções de web-crawling para buscar informações de cursos da UnB. O programa
# busca as informações com base em expressões regulares que, assume-se,
# representam a estrutura de uma página do Matrícula Web. Caso esta estrutura
# seja alterada, as expressões aqui precisam ser atualizadas de acordo.
#
# Erros em requests são ignorados silenciosamente.


import requests
import re

# Renomeando funções/classes para maior clareza de código.
busca = re.findall
RequestException = requests.exceptions.RequestException


def mweb(nivel, pagina, params, timeout=1):
    '''Retorna a página no Matrícula Web referente às especificações dadas.'''
    try:
        pagina = 'https://matriculaweb.unb.br/%s/%s.aspx' % (nivel, pagina)
        html = requests.get(pagina, params=params, timeout=timeout)
        return html.content
    except RequestException:  # as e:
        pass

    return ''


class Nivel:
    '''Enumeração de níveis de cursos oferecidos.'''
    GRADUACAO = 'graduacao'
    POS = 'posgraduacao'


class Campus:
    '''Enumeração dos códigos de cada campus.'''
    DARCY_RIBEIRO = 1
    PLANALTINA = 2
    CEILANDIA = 3
    GAMA = 4


class Departamento:
    '''Enumeração dos códigos de cada departamento.'''
    CIC = 116
    ENE = 163
    ENM = 164
    EST = 115
    GAMA = 650
    IFD = 550  # Instituto de Física
    MAT = 113


class Habilitacoes:
    '''Enumeração das habilitações de cada curso.'''
    BCC = 1856  # Ciência da Computação
    LIC = 1899  # Computação
    ENC = 1741  # Engenharia de Computação
    ENM = 6912  # Engenharia de Controle e Automação


class Cursos:
    '''Métodos de busca associados a informações de cursos.'''

    @staticmethod
    def curriculo(curso, nivel=Nivel.GRADUACAO, verbose=False):
        '''Acessa o Matrícula Web e retorna um dicionário com a lista de
        disciplinas definidas no currículo do curso.

        Argumentos:
        curso -- o código do curso
        nivel -- nível acadêmico do curso
                 (default Nivel.GRADUACAO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)

        No caso de disciplinas de cadeias seletivas, o resultado é uma lista em
        que cada item tem uma relação 'OU' com os demais, e cada item é um
        dicionário cujos itens têm uma relação 'E' entre si. Por exemplo:
        o resultado da busca por 6912 (Engenharia Mecatrônica) tem como uma das
        cadeias resultantes (a cadeia '2'), a seguinte lista:
        [{'114014': 'QUIMICA GERAL'}, {'114634': 'QUI GERAL EXPERIMENTAL',
                                       '114626': 'QUIMICA GERAL TEORICA'}]

        que deve ser interpretado como
        114014 OU (114626 E 114634)

        Ou seja, para graduação na habilitação 6912, é preciso ter sido
        aprovado na disciplina QUIMICA GERAL ou ter sido aprovado em ambas as
        disciplinas QUI GERAL EXPERIMENTAL e QUIMICA GERAL TEORICA.
        '''

        OBR_OPT = 'DISCIPLINAS OBRIGATÓRIAS (.*?)</table></td>(.*?)' \
                  'DISCIPLINAS OPTATIVAS (.*?)</table></td>'
        CADEIAS = 'CADEIA: (\d+)(.*?)</table>'
        DISCIPLINA = 'disciplina.aspx\?cod=(\d+)>.*?</b> - (.*?)</a></td>' \
                     '<td><b>(.*?)</b></td><td>(\d+) (\d+) (\d+) (\d+)</td>' \
                     '<td>(.*?)</td></tr>'

        curso = str(curso)
        if verbose:
            log('Buscando currículo do curso ' + curso)

        pagina_html = mweb(nivel, 'curriculo', {'cod': curso})
        obr_e_opts = busca(OBR_OPT, pagina_html)

        disciplinas = {'obrigatórias': {}, 'cadeias': {}, 'optativas': {}}
        for obrigatorias, cadeias, optativas in obr_e_opts:
            disciplinas['obrigatórias'] = {}
            for (cod, nome, e_ou, teor,
                 prat, ext, est, area) in busca(DISCIPLINA, obrigatorias):
                creditos = {'Teoria': int(teor), 'Prática': int(prat),
                            'Extensão': int(ext), 'Estudo': int(est)}
                disciplinas['obrigatórias'][cod] = {'Nome': nome.strip(),
                                                    'Créditos': creditos,
                                                    'Área': area.strip()}

            for ciclo, discs in busca(CADEIAS, cadeias):
                disciplinas['cadeias'][ciclo] = []
                current = {}
                for (cod, nome, e_ou, teor,
                     prat, ext, est, area) in busca(DISCIPLINA, discs):
                    creditos = {'Teoria': int(teor), 'Prática': int(prat),
                                'Extensão': int(ext), 'Estudo': int(est)}
                    current[cod] = {'Nome': nome.strip(),
                                    'Créditos': creditos,
                                    'Área': area.strip()}
                    if e_ou.strip() != 'E':
                        disciplinas['cadeias'][ciclo].append(current)
                        current = {}

            for (cod, nome, e_ou, teor,
                 prat, ext, est, area) in busca(DISCIPLINA, optativas):
                creditos = {'Teoria': int(teor), 'Prática': int(prat),
                            'Extensão': int(ext), 'Estudo': int(est)}
                disciplinas['optativas'][cod] = {'Nome': nome.strip(),
                                                 'Créditos': creditos,
                                                 'Área': area.strip()}

        return disciplinas

    @staticmethod
    def fluxo(habilitacao, nivel=Nivel.GRADUACAO, verbose=False):
        '''Acessa o Matrícula Web e retorna um dicionário com a lista de
        disciplinas por período definidas no fluxo da habilitação.

        Argumentos:
        habilitacao -- o código da habilitação do curso
        nivel -- nível acadêmico do curso
                 (default Nivel.GRADUACAO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)
        '''
        PERIODO = '<b>PERÍODO: (\d+).*?CRÉDITOS:</b> (\d+)</td>' \
                  '(.*?)</tr></table>'
        DISCIPLINA = 'disciplina.aspx\?cod=\d+>(\d+)</a>'

        habilitacao = str(habilitacao)
        if verbose:
            log('Buscando disciplinas no fluxo da habilitação ' +
                habilitacao)

        pagina_html = mweb(nivel, 'fluxo', {'cod': habilitacao})
        oferta = busca(PERIODO, pagina_html)

        disciplinas = {}
        for periodo, creditos, dados in oferta:
            periodo = int(periodo)
            disciplinas[periodo] = {}
            disciplinas[periodo]['Créditos'] = creditos
            disciplinas[periodo]['Disciplinas'] = busca(DISCIPLINA, dados)

        return disciplinas

    @staticmethod
    def habilitacoes(curso, nivel=Nivel.GRADUACAO,
                     campus=Campus.DARCY_RIBEIRO, verbose=False):
        '''Acessa o Matrícula Web e retorna um dicionário com a lista de
        informações referentes a cada habilitação no curso.

        Argumentos:
        curso -- o código do curso
        nivel -- nível acadêmico do curso
                 (default Nivel.GRADUACAO)
        campus -- o campus onde o curso é oferecido
                  (default DARCY_RIBEIRO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)
        '''
        OPCAO = '<a name=\d+></a><tr .*?><td  colspan=3><b>(\d+) - (.*?)' \
                '</b></td></tr>.*?' \
                'Grau: </td><td .*?>(.*?)</td></tr>.*?' \
                'Limite mínimo de permanência: </td>' \
                '<td align=right>(\d+)</td>.*?' \
                'Limite máximo de permanência: </td>.*?' \
                '<td align=right>(\d+)</td>.*?' \
                'Quantidade de Créditos para Formatura: </td>' \
                '<td align=right>(\d+)</td>.*?' \
                'Quantidade mínima de Créditos Optativos ' \
                'na Área de Concentração: </td>' \
                '<td align=right>(\d+)</td>.*?' \
                'Quantidade mínima de Créditos Optativos na Área Conexa: ' \
                '</td><td align=right>(\d+)</td>.*?' \
                'Quantidade máxima de Créditos no Módulo Livre: </td>' \
                '<td align=right>(\d+)</td>'

        curso = str(curso)
        if verbose:
            log('Buscando informações da habilitação do curso ' + curso)

        pagina_html = mweb(nivel, 'curso_dados', {'cod': curso})
        habilitacoes = busca(OPCAO, pagina_html)

        dados = {}
        for (habilitacao, nome, grau, l_min, l_max,
             formatura, obr, opt, livre) in habilitacoes:
            dados[habilitacao] = {}
            dados[habilitacao]['Nome'] = nome
            dados[habilitacao]['Grau'] = grau
            dados[habilitacao]['Limite mínimo de permanência'] = l_min
            dados[habilitacao]['Limite máximo de permanência'] = l_max
            dados[habilitacao]['Créditos para Formatura'] = formatura
            dados[habilitacao]['Mínimo de Créditos Optativos na '
                               'Área de Concentração'] = obr
            dados[habilitacao]['Quantidade mínima de Créditos Optativos '
                               'na Área Conexa'] = opt
            dados[habilitacao]['Quantidade máxima de Créditos no '
                               'Módulo Livre'] = livre
        return dados

    @staticmethod
    def relacao(nivel=Nivel.GRADUACAO, campus=Campus.DARCY_RIBEIRO,
                verbose=False):
        '''Acessa o Matrícula Web e retorna um dicionário com a relação de
        cursos existentes.

        Argumentos:
        nivel -- nível acadêmico dos cursos
                 (default Nivel.GRADUACAO)
        campus -- o campus onde o curso é oferecido
                  (default DARCY_RIBEIRO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)
        '''
        CURSOS = '<tr CLASS=PadraoMenor bgcolor=.*?>'\
                 '<td>(.*?)</td>' \
                 '<td>\d+</td>' \
                 '.*?aspx\?cod=(\d+)>(.*?)</a></td>' \
                 '<td>(.*?)</td></tr>'

        campus = str(campus)
        if verbose:
            log('Buscando lista de cursos para o campus ' + campus)

        pagina_html = mweb(nivel, 'curso_rel', {'cod': campus})
        cursos_existentes = busca(CURSOS, pagina_html)

        lista = {}
        for modalidade, codigo, denominacao, turno in cursos_existentes:
            lista[codigo] = {}
            lista[codigo]['Modalidade'] = modalidade
            lista[codigo]['Denominação'] = denominacao
            lista[codigo]['Turno'] = turno

        return lista


class Disciplina:
    '''Métodos de busca associados a informações de disciplinas.'''

    @staticmethod
    def informacoes(disciplina, nivel=Nivel.GRADUACAO, verbose=False):
        '''Acessa o Matrícula Web e retorna um dicionário com as informações da
        disciplina.

        Argumentos:
        disciplina -- o código da disciplina
        nivel -- nível acadêmico da disciplina
                 (default Nivel.GRADUACAO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)
        '''
        DISCIPLINAS = 'Órgão:</b> </td><td>(\w+) - (.*?)</td></tr>.*?' \
                      'Denominação:</b> </td><td>(.*?)</td></tr>.*?' \
                      'Nível:</b> </td><td>(.*?)</td></tr>.*?' \
                      'Vigência:</b> </td><td>(.*?)</td></tr>.*?' \
                      'Pré-req:</b> </td><td class=PadraoMenor>(.*?)' \
                      '</td></tr>.*?' \
                      'Ementa:</b> </td><td class=PadraoMenor>' \
                      '<p align=justify>(.*?)</P></td></tr>.*?' \
                      '(?:.*Programa:</b> </td><td class=PadraoMenor>' \
                      '<p align=justify>(.*?)</P></td></tr>)?.*?' \
                      'Bibliografia:</b> </td><td class=PadraoMenor>' \
                      '<p align=justify>(.*?)</P></td></tr>'

        disciplina = str(disciplina)
        if verbose:
            log('Buscando informações da disciplina ' + disciplina)

        pagina_html = mweb(nivel, 'disciplina', {'cod': disciplina})
        informacoes = busca(DISCIPLINAS, pagina_html)

        infos = {}
        for (sigla, nome, denominacao, nivel, vigencia,
             pre_req, ementa, programa, bibliografia) in informacoes:
            infos['Sigla do Departamento'] = sigla
            infos['Nome do Departamento'] = nome
            infos['Denominação'] = denominacao
            infos['Nível'] = nivel  # sobrescreve o argumento da função
            infos['Vigência'] = vigencia
            infos['Pré-requisitos'] = pre_req.replace('<br>', ' ')
            infos['Ementa'] = ementa.replace('<br />', '\n')
            if programa:
                infos['Programa'] = programa.replace('<br />', '\n')
            infos['Bibliografia'] = bibliografia.replace('<br />', '\n')

        return infos

    @staticmethod
    def pre_requisitos(disciplina, nivel=Nivel.GRADUACAO, verbose=False):
        '''Dado o código de uma disciplina, acessa o Matrícula Web e retorna
        uma lista com os códigos das disciplinas que são pré-requisitos para a
        dada.

        Argumentos:
        disciplina -- o código da disciplina
        nivel -- nível acadêmico da disciplina
                 (default Nivel.GRADUACAO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)

        Cada item da lista tem uma relação 'OU' com os demais, e cada item é
        uma outra lista cujos itens têm uma relação 'E' entre si. Por exemplo:
        o resultado da busca por 116424 (Transmissão de Dados) é:
        [['117251'], ['116394', '113042']]
        que deve ser interpretado como
        ['117251'] OU ['116394' E '113042']

        Ou seja, para cursar a disciplina 116424, é preciso ter sido aprovado
        na disciplina 117251 (ARQ DE PROCESSADORES DIGITAIS) ou ter sido
        aprovado nas disciplinas 116394 (ORG ARQ DE COMPUTADORES) e 113042
        (Cálculo 2).
        '''
        DISCIPLINAS = '<td valign=top><b>Pré-req:</b> </td>' \
                      '<td class=PadraoMenor>(.*?)</td></tr>'
        CODIGO = '(\d{6})'

        disciplina = str(disciplina)
        if verbose:
            log('Buscando a lista de pré-requisitos para a disciplina ' +
                disciplina)

        pagina_html = mweb(nivel, 'disciplina_pop', {'cod': disciplina})
        requisitos = busca(DISCIPLINAS, pagina_html)

        pre_reqs = []
        for req in requisitos:
            for disciplina in req.split(' OU<br>'):
                pre_reqs.append(busca(CODIGO, disciplina))

        return [codigo for codigo in pre_reqs if codigo]


class Oferta:
    '''Métodos de busca associados a informações da oferta de disciplinas.'''
    @staticmethod
    def departamentos(nivel=Nivel.GRADUACAO, campus=Campus.DARCY_RIBEIRO,
                      verbose=False):
        '''Acessa o Matrícula Web e retorna um dicionário com a lista de
        departamentos com ofertas do semestre atual.

        Argumentos:
        nivel -- nível acadêmico do Departamento
                 (default Nivel.GRADUACAO)
        campus -- o campus onde o curso é oferecido
                  (default Campus.DARCY_RIBEIRO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)
        '''
        DEPARTAMENTOS = '<tr CLASS=PadraoMenor bgcolor=.*?>'\
                        '<td>\d+</td><td>(\w+)</td>' \
                        '.*?aspx\?cod=(\d+)>(.*?)</a></td></tr>'

        if verbose:
            log('Buscando a informações de departamentos com oferta')

        pagina_html = mweb(nivel, 'oferta_dep', {'cod': str(campus)})
        deptos_existentes = busca(DEPARTAMENTOS, pagina_html)

        deptos = {}
        for sigla, codigo, denominacao in deptos_existentes:
            deptos[codigo] = {}
            deptos[codigo]['Sigla'] = sigla
            deptos[codigo]['Denominação'] = denominacao

        return deptos

    @staticmethod
    def disciplinas(departamento, nivel=Nivel.GRADUACAO, verbose=False):
        '''Acessa o Matrícula Web e retorna um dicionário com a lista de
        disciplinas ofertadas por um departamento.

        Argumentos:
        departamento -- o código do Departamento que oferece as disciplinas
        nivel -- nível acadêmico das disciplinas buscadas
                 (default Nivel.GRADUACAO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)

        Lista completa dos Departamentos da UnB:
        matriculaweb.unb.br/matriculaweb/graduacao/oferta_dep.aspx?cod=1
        '''
        DISCIPLINAS = 'oferta_dados.aspx\?cod=(\d+).*?>(.*?)</a>'

        departamento = str(departamento)
        if verbose:
            log('Buscando a informações de disciplinas do departamento ' +
                departamento)

        pagina_html = mweb(nivel, 'oferta_dis', {'cod': departamento})
        ofertadas = busca(DISCIPLINAS, pagina_html)

        oferta = {}
        for codigo, nome in ofertadas:
            oferta[codigo] = nome

        return oferta

    @staticmethod
    def lista_de_espera(disciplina, turma='\w+', nivel=Nivel.GRADUACAO,
                        verbose=False):
        '''Dado o código de uma disciplina, acessa o Matrícula Web e retorna um
        dicionário com a lista de espera para turmas ofertadas da disciplina.

        Argumentos:
        disciplina -- o código da disciplina
        turma -- identificador da turma
                 (default '\w+') (todas as disciplinas)
        nivel -- nível acadêmico da disciplina buscada
                 (default Nivel.GRADUACAO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)

        O argumento 'turma' deve ser uma expressão regular.
        '''
        TABELA = '<td><b>Turma</b></td>    ' \
                 '<td><b>Vagas<br>Solicitadas</b></td>  </tr>' \
                 '<tr CLASS=PadraoMenor bgcolor=.*?>  ' \
                 '.*?</tr><tr CLASS=PadraoBranco>'
        TURMAS = '<td align=center >(%s)</td>  ' \
                 '<td align=center >(\d+)</td></tr>' % turma

        disciplina = str(disciplina)
        if verbose:
            log('Buscando turmas com lista de espera para a disciplina ' +
                disciplina)

        pagina_html = mweb(nivel, 'faltavaga_rel', {'cod': disciplina})
        turmas_com_demanda = busca(TABELA, pagina_html)

        demanda = {}
        for tabela in turmas_com_demanda:
            for turma, vagas_desejadas in busca(TURMAS, tabela):
                vagas = int(vagas_desejadas)
                if vagas > 0:
                    demanda[turma] = vagas

        return demanda

    @staticmethod
    def oferta(disciplina, depto=None, nivel=Nivel.GRADUACAO,
               verbose=False):
        '''Dado o código de uma disciplina, e o do Departamento que a oferece,
        acessa o Matrícula Web e retorna um dicionário com a lista de turmas
        ofertadas para uma disciplina.

        Argumentos:
        disciplina -- o código da disciplina
        depto -- o código do departamento que oferece a disciplina
                 (default Departamento.CIC)
        nivel -- nível acadêmico da disciplina
                 (default Nivel.GRADUACAO)
        verbose -- indicação dos procedimentos sendo adotados
                   (default False)
        '''
        INFORMACOES = 'Departamento: <strong><a href.*?>(.*?)</a></strong>' \
                      '.*?' \
                      'Nome: <a title=.*?>(.*?)<img .*?></a>' \
                      '.*?' \
                      '<b>Créditos</b><br>\(Teor-Prat-Ext-Est\)<br>' \
                      '<font.*?>(\d+)-(\d+)-(\d+)-(\d+)'

        TURMAS = '<b>Turma</b>.*?<font size=4><b>(\w+)</b></font></div>' \
                 '.*?' \
                 '<td>Total</td><td>Vagas</td><td><b>(\d+)</b>' \
                 '.*?' \
                 '<td>Ocupadas</td>' \
                 '<td><b><font color=(?:red|green)>(\d+)</font></b></td>' \
                 '(.*?)' \
                 '<center>(.*?)(?:|<br>)</center>' \
                 '.*?' \
                 '(Reserva para curso(.*?))?' \
                 '<tr><td colspan=6 bgcolor=white height=20></td></tr>'

        HORARIO = '<b>((?:Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo))' \
                  '</b>.*?' \
                  '<font size=1 color=black><b>(.*?)</font>.*?' \
                  '<font size=1 color=brown>(.*?)</b></font><br><i>' \
                  '<img src=/imagens/subseta_dir.gif align=top> (.*?)</i>'

        RESERVA = '<td align=left>(.*?)</td>' \
                  '<td align=center>(\d+)</td>' \
                  '<td align=center>(\d+)</td>'

        disciplina = str(disciplina)
        if verbose:
            log('Buscando as turmas da disciplina ' + disciplina)

        params = {'cod': disciplina}
        if depto:
            params['dep'] = str(depto)

        pagina_html = mweb(nivel, 'oferta_dados', params)
        informacoes = busca(INFORMACOES, pagina_html)

        oferta = {}
        for (departamento, nome, teor, prat, ext, est) in informacoes:
            oferta['Departamento'] = departamento
            oferta['Nome'] = nome
            oferta['Créditos'] = {'Teoria': int(teor), 'Prática': int(prat),
                                  'Extensão': int(ext), 'Estudo': int(est)}

        turmas = busca(TURMAS, pagina_html)
        turmas_ofertadas = {}
        for (t, vagas, ocupadas, horarios, docentes, aux, reservas) in turmas:
            turma = {'Vagas': int(vagas),
                     'Alunos Matriculados': int(ocupadas),
                     'Professores': docentes.split('<br>')}

            turma['Aulas'] = {}
            for dia, inicio, fim, local in busca(HORARIO, horarios):
                if dia not in turma['Aulas']:
                    turma['Aulas'][dia] = []
                turma['Aulas'][dia].append({'Início': inicio,
                                            'Fim': fim,
                                            'Local': local})
            if reservas:
                turma['Turma Reservada'] = {curso: {'Vagas': int(vagas),
                                                    'Calouros': int(calouros)}
                                            for curso, vagas, calouros
                                            in busca(RESERVA, reservas)}

            turmas_ofertadas[t] = turma

        oferta['Turmas'] = turmas_ofertadas

        return oferta


def log(msg):
    '''Log de mensagens.'''
    print(msg)
