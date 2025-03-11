from flask import Flask, render_template, request, redirect, url_for
from dbfread import DBF
import logging
from datetime import datetime
import pandas as pd
from flask import Response

# Configuração do log
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Caminhos dos arquivos DBF
REQUISICAO_MATERIAIS_DB_PATH = r'C:\plantebem\Genesis\Dados\E01\REQUISICAOMATERIAIS.DBF'
REQUISICAO_PRODUTOS_DB_PATH = r'C:\plantebem\Genesis\Dados\E01\REQUISICAOMATERIAISPRODUTOS.DBF'
NOTA_FISCAL_ITENS_DB_PATH = r'C:\plantebem\Genesis\Dados\E01\NOTAFISCALENTRADAITENS.DBF'
NOTA_FISCAL_DB_PATH = r'C:\plantebem\Genesis\Dados\E01\NOTAFISCALENTRADA.DBF'

def formatar_data(data):
    """ Converte a data para o formato dd/mm/yy """
    try:
        if hasattr(data, "strftime"):
            return data.strftime("%d/%m/%y")
        if isinstance(data, str):
            try:
                return datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%y")
            except ValueError:
                return datetime.strptime(data, "%Y%m%d").strftime("%d/%m/%y")
    except Exception:
        return data

def to_float(value):
    """ Converte um valor para float, evitando erro ao formatar """
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def ler_dbf(caminho):
    """ Função para ler arquivos DBF com tratamento de erro """
    try:
        return DBF(caminho, encoding='latin1')
    except Exception as e:
        logging.error(f"Erro ao abrir {caminho}: {e}")
        return None

@app.route('/', methods=['GET'])
def index():
    try:
        logging.info("Iniciando a leitura dos arquivos DBF")

        # Captura os filtros da URL
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        codigo_produto = request.args.get('codigo_produto', '').strip()
        descricao_produto = request.args.get('descricao_produto', '').strip().lower()

        # Converter datas para comparação
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d") if data_inicio else None
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") if data_fim else None

        logging.info(f"Filtros aplicados - Data Início: {data_inicio}, Data Fim: {data_fim}, Código Produto: {codigo_produto}, Descrição Produto: {descricao_produto}")

        # Ler os arquivos DBF
        requisicao_materiais_table = ler_dbf(REQUISICAO_MATERIAIS_DB_PATH)
        requisicao_produtos_table = ler_dbf(REQUISICAO_PRODUTOS_DB_PATH)
        nota_fiscal_itens_table = ler_dbf(NOTA_FISCAL_ITENS_DB_PATH)
        nota_fiscal_table = ler_dbf(NOTA_FISCAL_DB_PATH)

        if not all([requisicao_materiais_table, requisicao_produtos_table, nota_fiscal_itens_table, nota_fiscal_table]):
            return "Erro ao carregar os arquivos DBF. Verifique os logs.", 500

        logging.info("Arquivos DBF carregados com sucesso")

        # Criar dicionário para mapear NROLAN → DATA da requisição
        requisicao_data_map = {}
        for record in requisicao_materiais_table:
            nrolan = record.get('NROLAN')
            data_requisicao = record.get('DATA')
            if nrolan and data_requisicao:
                requisicao_data_map[nrolan] = formatar_data(data_requisicao)

        # Criar dicionário para mapear dados da nota fiscal
        nota_fiscal_map = {}
        for record in nota_fiscal_table:
            sequencial = record.get('SEQUENCIAL')
            lancamento = record.get('LANCAMENTO')
            if sequencial and lancamento:
                nota_fiscal_map[sequencial] = (formatar_data(lancamento), record.get('DOCUMENTO', 'Desconhecido'))

        # Criar dicionário para mapear dados da nota fiscal pelos códigos de produto
        nota_fiscal_itens_map = {}
        for record in nota_fiscal_itens_table:
            codigo_produto = record.get('CODIGO')
            sequencial = record.get('SEQUENCIAL')
            quantidade_nf = to_float(record.get('QUANTIDADE'))
            desconto = to_float(record.get('DESVALOR'))
            valor_unitario_nf = to_float(record.get('VALOR'))

            if codigo_produto and sequencial and sequencial in nota_fiscal_map:
                total_nf = to_float(record.get('TOTAL'))
                icms = to_float(record.get('VALORICMS'))
                pis = to_float(record.get('BASEPISCOF'))
                cofins = to_float(record.get('BASEPISCOF'))

                icms_unitario = icms / quantidade_nf if quantidade_nf > 0 else 0

                nota_fiscal_itens_map[codigo_produto] = (
                    total_nf, icms, pis, cofins,
                    nota_fiscal_map[sequencial][0],
                    nota_fiscal_map[sequencial][1],
                    quantidade_nf, desconto, valor_unitario_nf, icms_unitario
                )

        # Construir lista de dados combinados
        dados_combinados = []
        for record in requisicao_produtos_table:
            nrolan = record.get('NROLAN')
            cod_pro = record.get('CODPRO')

            if not cod_pro or not nrolan:
                continue

            data_requisicao = requisicao_data_map.get(nrolan, 'Desconhecido')
            if data_inicio_dt and data_requisicao != 'Desconhecido':
                data_requisicao_dt = datetime.strptime(data_requisicao, "%d/%m/%y")
                if (data_inicio_dt and data_requisicao_dt < data_inicio_dt) or (data_fim_dt and data_requisicao_dt > data_fim_dt):
                    continue

            des_pro = record.get('DESPRO', 'Desconhecido').lower()
            if descricao_produto and descricao_produto not in des_pro:
                continue

            quantidade_req = to_float(record.get('QUANTIDADE'))
            custo_unitario = to_float(record.get('CUSMED'))
            total_requisicao = quantidade_req * custo_unitario

            total_nf, icms_nf, pis_nf, cofins_nf, lancamento, documento, quantidade_nf, desconto, valor_unitario_nf, icms_unitario = nota_fiscal_itens_map.get(
                cod_pro, (0, 0, 0, 0, 'Desconhecido', 'Desconhecido', 0, 0, 0, 0)
            )

            icms_qnt_req = icms_unitario * quantidade_req
            bc_pis_req = (pis_nf / quantidade_nf) * quantidade_req if quantidade_nf > 0 else 0
            pis_final = round(pis_nf * 0.0165, 2)
            bc_cofins_req = (cofins_nf / quantidade_nf) * quantidade_req if quantidade_nf > 0 else 0
            cofins_final = round(cofins_nf * 0.0760, 2)

            dados_combinados.append((data_requisicao, cod_pro, des_pro, quantidade_req, custo_unitario, total_requisicao, documento, lancamento, quantidade_nf, valor_unitario_nf, desconto, total_nf, icms_nf, icms_unitario, pis_nf, cofins_nf, icms_qnt_req, bc_pis_req, '1,65%', pis_final, bc_cofins_req, '7,60%', cofins_final))

        return render_template('index.html', dados_combinados=dados_combinados)

    except Exception as e:
        logging.error(f"Erro ao ler os arquivos DBF: {e}")
        return f"Erro ao ler os arquivos DBF: {e}", 500
    
@app.route('/exportar', methods=['GET'])
def exportar_excel():
    try:
        logging.info("Exportando relatório para Excel")

        # Captura os filtros da URL
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        descricao_produto = request.args.get('descricao_produto', '').strip().lower()

        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d") if data_inicio else None
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") if data_fim else None

        # Garantir que os dados estejam carregados
        requisicao_materiais_table = ler_dbf(REQUISICAO_MATERIAIS_DB_PATH)
        requisicao_produtos_table = ler_dbf(REQUISICAO_PRODUTOS_DB_PATH)
        nota_fiscal_itens_table = ler_dbf(NOTA_FISCAL_ITENS_DB_PATH)
        nota_fiscal_table = ler_dbf(NOTA_FISCAL_DB_PATH)

        if not all([requisicao_materiais_table, requisicao_produtos_table, nota_fiscal_itens_table, nota_fiscal_table]):
            return "Erro ao carregar os arquivos DBF.", 500

        # Criar dicionário para mapear os dados da requisição e notas fiscais
        requisicao_data_map = {}
        for record in requisicao_materiais_table:
            nrolan = record.get('NROLAN')
            data_requisicao = record.get('DATA')
            if nrolan and data_requisicao:
                requisicao_data_map[nrolan] = formatar_data(data_requisicao)

        nota_fiscal_map = {}
        for record in nota_fiscal_table:
            sequencial = record.get('SEQUENCIAL')
            lancamento = record.get('LANCAMENTO')
            if sequencial and lancamento:
                nota_fiscal_map[sequencial] = (formatar_data(lancamento), record.get('DOCUMENTO', 'Desconhecido'))

        nota_fiscal_itens_map = {}
        for record in nota_fiscal_itens_table:
            codigo_produto = record.get('CODIGO')
            sequencial = record.get('SEQUENCIAL')
            quantidade_nf = to_float(record.get('QUANTIDADE'))
            desconto = to_float(record.get('DESVALOR'))
            valor_unitario_nf = to_float(record.get('VALOR'))

            if codigo_produto and sequencial and sequencial in nota_fiscal_map:
                total_nf = to_float(record.get('TOTAL'))
                icms = to_float(record.get('VALORICMS'))
                pis = to_float(record.get('BASEPISCOF'))
                cofins = to_float(record.get('BASEPISCOF'))

                icms_unitario = icms / quantidade_nf if quantidade_nf > 0 else 0

                nota_fiscal_itens_map[codigo_produto] = (
                    total_nf, icms, pis, cofins,
                    nota_fiscal_map[sequencial][0],
                    nota_fiscal_map[sequencial][1],
                    quantidade_nf, desconto, valor_unitario_nf, icms_unitario
                )

        # Construir lista de dados combinados filtrados
        dados_filtrados = []
        for record in requisicao_produtos_table:
            nrolan = record.get('NROLAN')
            cod_pro = record.get('CODPRO')

            if not cod_pro or not nrolan:
                continue

            data_requisicao = requisicao_data_map.get(nrolan, 'Desconhecido')
            if data_inicio_dt and data_requisicao != 'Desconhecido':
                data_requisicao_dt = datetime.strptime(data_requisicao, "%d/%m/%y")
                if (data_inicio_dt and data_requisicao_dt < data_inicio_dt) or (data_fim_dt and data_requisicao_dt > data_fim_dt):
                    continue

            des_pro = record.get('DESPRO', 'Desconhecido').lower()
            if descricao_produto and descricao_produto not in des_pro:
                continue

            quantidade_req = to_float(record.get('QUANTIDADE'))
            custo_unitario = to_float(record.get('CUSMED'))
            total_requisicao = quantidade_req * custo_unitario

            total_nf, icms_nf, pis_nf, cofins_nf, lancamento, documento, quantidade_nf, desconto, valor_unitario_nf, icms_unitario = nota_fiscal_itens_map.get(
                cod_pro, (0, 0, 0, 0, 'Desconhecido', 'Desconhecido', 0, 0, 0, 0)
            )

            icms_qnt_req = icms_unitario * quantidade_req
            bc_pis_req = (pis_nf / quantidade_nf) * quantidade_req if quantidade_nf > 0 else 0
            pis_final = round(pis_nf * 0.0165, 2)
            bc_cofins_req = (cofins_nf / quantidade_nf) * quantidade_req if quantidade_nf > 0 else 0
            cofins_final = round(cofins_nf * 0.0760, 2)

            dados_filtrados.append([
                data_requisicao, cod_pro, des_pro, quantidade_req, custo_unitario, total_requisicao, documento, lancamento, 
                quantidade_nf, valor_unitario_nf, desconto, total_nf, icms_nf, icms_unitario, pis_nf, cofins_nf, icms_qnt_req, 
                bc_pis_req, '1,65%', pis_final, bc_cofins_req, '7,60%', cofins_final
            ])

        # Criar um DataFrame Pandas
        colunas = [
            "Data Requisição", "Código Produto", "Descrição", "Quantidade Requisição",
            "Custo Unitário", "Total Requisição", "Número NF de Compra", "Data NF de Compra",
            "Quantidade NF de Compra", "Valor Unitário NF", "Desconto NF de Compra", "Total NF de Compra",
            "ICMS NF de Compra", "ICMS Unitário", "PIS", "COFINS", "ICMS QNT REQ.",
            "BC PIS REQ.", "Alíquota PIS", "PIS FINAL", "BC COFINS REQ.", "Alíquota COFINS", "COFINS FINAL"
        ]
        df = pd.DataFrame(dados_filtrados, columns=colunas)

        # Salvar o arquivo Excel
        excel_path = "C:\plantebem\Relatorio_Requisicoes_Notas.xlsx"
        df.to_excel(excel_path, index=False, sheet_name="Relatório")

        # Retornar o arquivo para download
        with open(excel_path, 'rb') as f:
            data = f.read()

        response = Response(data, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = "attachment; filename=Relatorio_Requisicoes_Notas.xlsx"
        return response

    except Exception as e:
        logging.error(f"Erro ao exportar para Excel: {e}")
        return f"Erro ao exportar para Excel: {e}", 500
    
if __name__ == '__main__':
    app.run(debug=True)
