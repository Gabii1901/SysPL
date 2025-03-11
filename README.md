# 📌 Relatório de Requisições e Notas Fiscais

Este projeto é um aplicativo web desenvolvido com **Flask**, que permite a leitura e análise de arquivos **DBF** para gerar relatórios de requisições e notas fiscais. Ele também possibilita a exportação dos dados filtrados para **Excel**.

---

## 🚀 **Funcionalidades**

✅ Leitura de arquivos **DBF** com requisições e notas fiscais  
✅ Filtros por **data e descrição**  
✅ Exibição dos dados em uma **tabela interativa**  
✅ Exportação dos dados filtrados para **Excel (.xlsx)**  
✅ Encerramento automático do servidor ao fechar a aba do navegador  

---

## 📂 **Estrutura do Projeto**

```
📁 projeto-relatorio
│── 📂 static         # Arquivos CSS, JS e ícones
│── 📂 templates      # Arquivos HTML
│── app.py           # Código principal do Flask
│── requirements.txt # Dependências do projeto
│── README.md        # Documentação do projeto
```

---

## 🛠 **Instalação e Configuração**

### **1️⃣ Clonar o repositório**
```bash
$ git clone https://github.com/seu-usuario/projeto-relatorio.git
$ cd projeto-relatorio
```

### **2️⃣ Criar um ambiente virtual e instalar dependências**
```bash
$ python -m venv venv
$ source venv/bin/activate  # Linux/macOS
$ venv\Scripts\activate    # Windows
$ pip install -r requirements.txt
```

### **3️⃣ Executar o projeto**
```bash
$ python app.py
```
O aplicativo estará acessível em: **http://127.0.0.1:5000**

---

## 📤 **Exportação para Excel**
Para exportar os dados filtrados, clique no botão **"Exportar para Excel"**. O arquivo será gerado no formato `.xlsx` sem o prefixo "R$" nas colunas numéricas.

---

## 🖥 **Encerramento Automático**
O aplicativo fecha automaticamente quando a aba do navegador é fechada, garantindo que o servidor Flask não continue em execução no terminal.

---

## 🔧 **Dependências**

As bibliotecas utilizadas estão listadas no `requirements.txt`:

```txt
Flask
pandas
xlsxwriter
dbfread
```
Para instalar todas as dependências, use:
```bash
$ pip install -r requirements.txt
```

---

## 🛠 **Empacotamento para Executável**
Para transformar o projeto em um executável, use **PyInstaller**:

```bash
$ pip install pyinstaller
$ pyinstaller --onefile --windowed --name=RelatorioApp app.py
```
Isso criará um executável dentro da pasta `dist/`.

---

## 📄 **Licença**

Este projeto é de uso livre. Sinta-se à vontade para contribuir e aprimorar! 🎉

Feito com ❤️ por Gabriela 🚀


