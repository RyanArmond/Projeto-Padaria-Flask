from flask import Flask
from flask import render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_simplelogin import SimpleLogin, login_required
from sqlalchemy import func
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///padaria.db"
app.config["SECRET_KEY"] = "f2d1a03ef96d5aad946426dfdbdd7ccd"
app.config["SIMPLELOGIN_USERNAME"] = "RyanArmond"
app.config["SIMPLELOGIN_PASSWORD"] = "ryan1234"
db = SQLAlchemy()
db.init_app(app)
SimpleLogin(app)

class Produto(db.Model):
    __tablename__ = 'produto'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(500))
    ingredientes = db.Column(db.String(500))
    origem = db.Column(db.String(100))
    imagem = db.Column(db.String(100))
    
    def __init__(self,
                 nome: str,
                 descricao: str,
                 ingredientes: str,
                 origem: str,
                 imagem: str):
        self.nome = nome
        self.descricao = descricao
        self.ingredientes = ingredientes
        self.origem = origem
        self.imagem = imagem
        
    
@app.route("/")
@login_required
def home():
    return render_template('index.html')

@app.route("/produtos", methods=['GET', 'POST'])
@login_required
def produtos_pagina():
    if request.method == "POST":
        termo = request.form["pesquisa"]
        resultado = db.session.execute(db.select(Produto)
                                       .filter(Produto.nome.like(f"%{termo}%"))).scalars()
        return render_template('produtos.html', produtos=resultado)

    produtos = db.session.execute(db.select(Produto)).scalars()
    return render_template('produtos.html', produtos=produtos)

@app.route("/cadastrar_produto", methods=["GET", "POST"])
@login_required
def cadastrar_produto():
    
    if request.method == "POST":
        status = {"tipo": "sucesso",
                  "mensagem": "Produto cadastrado com sucesso!"}
        dados = request.form
        imagem = request.files["imagem"]
        try:
            produto = Produto(dados['nome'],
                            dados['descricao'],
                            dados['ingredientes'],
                            dados['origem'],
                            imagem.filename)
            
            imagem.save(os.path.join("static/imagens", imagem.filename))
            db.session.add(produto)
            db.session.commit()
        except Exception:
            status = {"tipo": "erro",
                      "mensagem": f"Houve um problema ao cadastrar o produto {dados['nome']}"}    
        return render_template('cadastrar.html', status=status)
    else:
        return render_template('cadastrar.html')

@app.route("/editar_produtos/<int:id>", methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    # Buscando produto a ser editado
    produto_editar = db.session.execute(db.select(Produto).filter(Produto.id == id)).scalar()
    
    # Testando se o produto a ser editado existe
    if not produto_editar:
        flash("Produto não encontrado.")
        return redirect(url_for('produtos_pagina'))
    
    # Caso seja um POST
    if request.method == "POST":
        dados = request.form
        imagem = request.files.get("imagem")
        
        # Verificando se uma nova imagem foi enviada
        if imagem and imagem.filename:
            nova_imagem_enviada = True
            imagem_nome = imagem.filename
            
            # Verificando se uma imagem antiga existia
            if produto_editar.imagem and os.path.exists(os.path.join("static/imagens", produto_editar.imagem)):
                # Verificando se mais de um produto utilizava a imagem antiga
                quant_produtos_mesma_imagem = db.session.execute(
                    db.select(func.count(Produto.id)).filter(Produto.imagem == produto_editar.imagem)).scalar()

                # Tentando deletar a imagem antiga 
                if quant_produtos_mesma_imagem == 1:
                    try:
                        os.remove(os.path.join("static/imagens", produto_editar.imagem))
                    except OSError as e:
                        print(f"DEBUG: Erro ao remover imagem antiga {e}")
        else:
            nova_imagem_enviada = False
            imagem_nome = produto_editar.imagem
        
        # Editando o produto
        try:
            produto_editar.nome = dados.get('nome') or None
            produto_editar.descricao = dados.get('descricao') or None
            produto_editar.origem = dados.get('origem') or None
            produto_editar.ingredientes = dados.get('ingredientes') or None
            produto_editar.imagem = imagem_nome
            
            # Salvando a nova imagem
            if nova_imagem_enviada:
                caminho_salvar_imagem = os.path.join("static/imagens", imagem_nome)
                os.makedirs(os.path.dirname(caminho_salvar_imagem), exist_ok=True)
                imagem.save(caminho_salvar_imagem)         
        
            db.session.commit()

            flash("Produto editado com sucesso!")
            return redirect(url_for("produtos_pagina"))
        except Exception:
            db.session.rollback()
            status = {"tipo": "erro",
                      "mensagem": "erro ao editar produto"}
            
            return render_template("editar.html", produto=produto_editar, status=status)

    return render_template("editar.html", produto=produto_editar)

@app.route("/deletar_produto/<int:id>", methods=['GET'])
@login_required
def deletar_produto(id):
    produto_deletar = db.session.execute(db.select(Produto).filter_by(id=id)).scalar()
    try:
        db.session.delete(produto_deletar)
        db.session.commit()
        flash("Produto removido com sucesso!")
        return redirect(url_for("produtos_pagina"))
    except Exception:
        flash("Erro ao remover produto")
        return redirect(url_for("produtos_pagina"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run()