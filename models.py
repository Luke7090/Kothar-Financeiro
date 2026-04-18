from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Equipamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100))

    # Energia e custo
    potencia_w = db.Column(db.Float)          # watts
    manutencao_hora = db.Column(db.Float)     # R$/hora

    # Calibração mecânica
    retracao = db.Column(db.Float)

    # Dinâmica
    zona_vfa = db.Column(db.String(100))
    vfa_ideal = db.Column(db.Float)
    desvio_juncao = db.Column(db.Float)

    # Modelagem de entrada
    fme = db.Column(db.Float)
    fame = db.Column(db.Float)


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    custo_grama = db.Column(db.Float)
    estoque = db.Column(db.Float)

class PerfilMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    tipo = db.Column(db.String(50))
    fabricante = db.Column(db.String(100))
    temp_min = db.Column(db.Integer)
    temp_max = db.Column(db.Integer)
    temp_ideal = db.Column(db.Integer)
    fluxo = db.Column(db.Float)
    pressure_advance = db.Column(db.Float)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'))

class PerfilMaquina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    velocidade = db.Column(db.Float)
    aceleracao = db.Column(db.Integer)
    pa_padrao = db.Column(db.Float)
    equipamento_id = db.Column(db.Integer, db.ForeignKey('equipamento.id'))

class ItemAlmoxarifado(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(100), nullable=False)
    fabricante = db.Column(db.String(100))
    cor = db.Column(db.String(50))

    categoria = db.Column(db.String(50), nullable=False)
    unidade = db.Column(db.String(20), nullable=False)

    quantidade = db.Column(db.Float, default=0)
    custo_unitario = db.Column(db.Float, default=0)

class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Energia
    tarifa_energia = db.Column(db.Float, default=0)
    
    # Preço
    margem_promocional = db.Column(db.Float, default=0)
    margem_venda = db.Column(db.Float, default=0)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(100), nullable=False)

    equipamento_id = db.Column(db.Integer, db.ForeignKey('equipamento.id'))
    material_id = db.Column(db.Integer, db.ForeignKey('item_almoxarifado.id'))

    tempo_producao = db.Column(db.Float, default=0.0)       # horas
    quantidade_material = db.Column(db.Float, default=0.0)  # gramas

    energia = db.Column(db.Float, default=0.0)
    material_custo = db.Column(db.Float, default=0.0)
    custo_total = db.Column(db.Float, default=0.0)

    preco_promocional = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)

    material_nome = db.Column(db.String(100))
    material_fabricante = db.Column(db.String(100))
    material_cor = db.Column(db.String(50))

    equipamento = db.relationship('Equipamento')
    material = db.relationship('ItemAlmoxarifado')



class Produzido(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)

    nome = db.Column(db.String(100), nullable=False)
    material_nome = db.Column(db.String(100))
    material_fabricante = db.Column(db.String(100))
    material_cor = db.Column(db.String(50))

    quantidade = db.Column(db.Integer, default=0)

    peso_unitario_g = db.Column(db.Float, default=0.0)
    tempo_unitario_horas = db.Column(db.Float, default=0.0)

    custo_unitario = db.Column(db.Float, default=0.0)
    valor_total_estoque = db.Column(db.Float, default=0.0)

    disponivel = db.Column(db.Boolean, default=True)

    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    produto = db.relationship('Produto')


class Vendido(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)

    nome = db.Column(db.String(100), nullable=False)
    material_nome = db.Column(db.String(100))
    material_cor = db.Column(db.String(50))

    quantidade = db.Column(db.Integer, default=0)

    valor_venda_unitario = db.Column(db.Float, default=0.0)
    valor_venda_total = db.Column(db.Float, default=0.0)

    custo_unitario = db.Column(db.Float, default=0.0)
    custo_total = db.Column(db.Float, default=0.0)

    lucro_total = db.Column(db.Float, default=0.0)

    produto = db.relationship('Produto')


class Reaproveitamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True)

    # identifica se a linha é material ou item de manutenção
    categoria_item = db.Column(db.String(20), nullable=False, default="material")
    # "material" ou "manutencao"

    # material
    material_nome = db.Column(db.String(100))
    material_cor = db.Column(db.String(50))
    material_fabricante = db.Column(db.String(100))

    # item de manutenção
    item_nome = db.Column(db.String(100))

    unidade = db.Column(db.String(20), nullable=False, default='g')
    motivo = db.Column(db.String(50), nullable=False)

    quantidade = db.Column(db.Float, default=0.0)

    valor_unitario = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)

    tempo_gasto_reais = db.Column(db.Float, default=0.0)

    origem = db.Column(db.String(50), default='manual')
    # "manual" ou "produzidos"

    produto = db.relationship('Produto')