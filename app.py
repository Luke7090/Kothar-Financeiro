from flask import Flask, render_template, request, redirect, url_for
from collections import defaultdict
from models import (
    db,
    Equipamento,
    Material,
    PerfilMaterial,
    PerfilMaquina,
    ItemAlmoxarifado,
    Configuracao,
    Produto,
    Produzido,
    Vendido,
    Reaproveitamento,
)

# ---------------- FUNÇÕES AUXILIARES ----------------
def to_float(valor):
    if valor is None or valor == "":
        return 0.0
    return float(valor.replace(",", "."))

def to_int(valor):
    if valor is None or valor == "":
        return 0
    return int(valor)

# ---------------- APP ----------------
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    config = Configuracao.query.first()

    if not config:
        config = Configuracao(
            tarifa_energia=0.0,
            margem_promocional=0.6,
            margem_venda=0.5
        )
        db.session.add(config)
        db.session.commit()

    if request.method == "POST":
        config.tarifa_energia = to_float(request.form.get("tarifa_energia"))
        config.margem_promocional = to_float(request.form.get("margem_promocional"))
        config.margem_venda = to_float(request.form.get("margem_venda"))

        # proteção contra divisão por zero
        if config.margem_promocional <= 0:
            config.margem_promocional = 0.6

        if config.margem_venda <= 0:
            config.margem_venda = 0.5

        db.session.commit()
        return redirect("/")

    return render_template(
        "index.html",
        tarifa_energia=config.tarifa_energia,
        margem_promocional=config.margem_promocional,
        margem_venda=config.margem_venda
    )

# ---------------- EQUIPAMENTOS ----------------
@app.route("/equipamentos", methods=["GET", "POST"])
def equipamentos():
    if request.method == "POST":
        equipamento = Equipamento(
            nome=request.form.get("nome"),
            modelo=request.form.get("modelo"),
            potencia_w=to_float(request.form.get("potencia_w")),
            manutencao_hora=to_float(request.form.get("manutencao_hora")),
            retracao=to_float(request.form.get("retracao")),
            zona_vfa=request.form.get("zona_vfa"),
            vfa_ideal=to_float(request.form.get("vfa_ideal")),
            desvio_juncao=to_float(request.form.get("desvio_juncao")),
            fme=to_float(request.form.get("fme")),
            fame=to_float(request.form.get("fame"))
        )

        db.session.add(equipamento)
        db.session.commit()

        return redirect("/equipamentos")

    equipamentos = Equipamento.query.order_by(Equipamento.id.desc()).all()
    return render_template("equipamentos.html", equipamentos=equipamentos)

@app.route("/equipamentos/deletar/<int:id>", methods=["POST"])
def deletar_equipamento(id):
    equipamento = Equipamento.query.get_or_404(id)
    db.session.delete(equipamento)
    db.session.commit()
    return redirect("/equipamentos")

@app.route("/equipamentos/editar/<int:id>", methods=["GET", "POST"])
def editar_equipamento(id):
    equipamento = Equipamento.query.get_or_404(id)

    if request.method == "POST":
        equipamento.nome = request.form.get("nome")
        equipamento.modelo = request.form.get("modelo")
        equipamento.potencia_w = to_float(request.form.get("potencia_w"))
        equipamento.manutencao_hora = to_float(request.form.get("manutencao_hora"))
        equipamento.retracao = to_float(request.form.get("retracao"))
        equipamento.zona_vfa = request.form.get("zona_vfa")
        equipamento.vfa_ideal = to_float(request.form.get("vfa_ideal"))
        equipamento.desvio_juncao = to_float(request.form.get("desvio_juncao"))
        equipamento.fme = to_float(request.form.get("fme"))
        equipamento.fame = to_float(request.form.get("fame"))

        db.session.commit()
        return redirect("/equipamentos")

    return render_template("equipamentos_editar.html", equipamento=equipamento)

# ---------------- ALMOXARIFADO ----------------
@app.route("/almoxarifado", methods=["GET", "POST"])
def almoxarifado():
    if request.method == "POST":
        nome = request.form.get("nome")
        fabricante = request.form.get("fabricante")
        cor = request.form.get("cor")
        categoria = request.form.get("categoria")
        unidade = request.form.get("unidade")
        quantidade = to_float(request.form.get("quantidade"))
        custo_unitario = to_float(request.form.get("custo_unitario"))
        aba = request.form.get("aba", "materiais")

        # Se for material, evita duplicação e faz média ponderada
        if categoria == "material":
            existente = ItemAlmoxarifado.query.filter_by(
                nome=nome,
                fabricante=fabricante,
                cor=cor,
                categoria="material",
                unidade="g"
            ).first()

            if existente:
                estoque_atual = existente.quantidade or 0.0
                preco_atual = existente.custo_unitario or 0.0

                novo_preco_kg = (
                    (estoque_atual * preco_atual) +
                    (quantidade * custo_unitario)
                ) / (estoque_atual + quantidade)

                existente.quantidade = estoque_atual + quantidade
                existente.custo_unitario = novo_preco_kg
            else:
                item = ItemAlmoxarifado(
                    nome=nome,
                    fabricante=fabricante,
                    cor=cor,
                    categoria=categoria,
                    unidade=unidade,
                    quantidade=quantidade,
                    custo_unitario=custo_unitario
                )
                db.session.add(item)

        # Itens de manutenção continuam criando normalmente
        else:
            item = ItemAlmoxarifado(
                nome=nome,
                fabricante=fabricante,
                cor=cor,
                categoria=categoria,
                unidade=unidade,
                quantidade=quantidade,
                custo_unitario=custo_unitario
            )
            db.session.add(item)

        db.session.commit()
        return redirect(f"/almoxarifado?aba={aba}")

    itens = ItemAlmoxarifado.query.all()
    return render_template("almoxarifado.html", itens=itens)

# ---------------- REPOSIÇÃO MATERIAL ----------------
@app.route("/almoxarifado/repor/<int:id>", methods=["POST"])
def repor_material(id):
    item = ItemAlmoxarifado.query.get_or_404(id)

    quantidade_nova = to_float(request.form.get("quantidade"))
    preco_novo_kg = to_float(request.form.get("preco_compra"))

    if quantidade_nova <= 0 or preco_novo_kg <= 0:
        return redirect("/almoxarifado?aba=materiais")

    quantidade_atual = item.quantidade or 0.0
    preco_atual_kg = item.custo_unitario or 0.0

    novo_preco_kg = (
        (quantidade_atual * preco_atual_kg) +
        (quantidade_nova * preco_novo_kg)
    ) / (quantidade_atual + quantidade_nova)

    item.quantidade = quantidade_atual + quantidade_nova
    item.custo_unitario = novo_preco_kg

    db.session.commit()
    return redirect("/almoxarifado?aba=materiais")

# ---------------- REPOSIÇÃO MANUTENÇÃO ----------------
@app.route("/almoxarifado/repor-manutencao/<int:id>", methods=["POST"])
def repor_item_manutencao(id):
    item = ItemAlmoxarifado.query.get_or_404(id)

    quantidade = to_float(request.form.get("quantidade"))
    custo_unitario = to_float(request.form.get("custo_unitario"))

    if quantidade <= 0 or custo_unitario <= 0:
        return redirect("/almoxarifado?aba=manutencao")

    item.quantidade += quantidade
    item.custo_unitario = custo_unitario

    db.session.commit()
    return redirect("/almoxarifado?aba=manutencao")

# ---------------- EXCLUIR ITEM ----------------
@app.route("/almoxarifado/deletar/<int:id>", methods=["POST"])
def deletar_item_almoxarifado(id):
    item = ItemAlmoxarifado.query.get_or_404(id)
    categoria = item.categoria

    db.session.delete(item)
    db.session.commit()

    aba = "manutencao" if categoria == "manutencao" else "materiais"
    return redirect(f"/almoxarifado?aba={aba}")

# ---------------- Produtos ----------------
@app.route("/produtos", methods=["GET", "POST"])
def produtos():
    produtos = Produto.query.all()
    equipamentos = Equipamento.query.all()
    materiais = ItemAlmoxarifado.query.filter_by(categoria="material").all()

    config = Configuracao.query.first()
    if not config:
        config = Configuracao(
            tarifa_energia=0.0,
            margem_promocional=0.6,
            margem_venda=0.5
        )
        db.session.add(config)
        db.session.commit()

    margem_promocional = config.margem_promocional if config.margem_promocional > 0 else 0.6
    margem_venda = config.margem_venda if config.margem_venda > 0 else 0.5

    if request.method == "POST":
        nome = request.form.get("nome")
        equipamento_id = to_int(request.form.get("equipamento_id"))
        material_id = to_int(request.form.get("material_id"))
        tempo_producao = to_float(request.form.get("tempo_producao"))  # em minutos
        quantidade_material = to_float(request.form.get("quantidade_material"))

        equipamento = Equipamento.query.get(equipamento_id)
        material = ItemAlmoxarifado.query.get(material_id)

        tarifa_energia = config.tarifa_energia if config.tarifa_energia > 0 else 0.0

        # converte minutos para horas
        tempo_horas = tempo_producao / 60

        energia = ((equipamento.potencia_w or 0) / 1000) * tempo_horas * tarifa_energia
        material_custo = quantidade_material * ((material.custo_unitario or 0) / 1000)
        custo_manutencao = tempo_horas * (equipamento.manutencao_hora or 0)

        custo_total = energia + material_custo + custo_manutencao

        preco_promocional = custo_total / margem_promocional
        preco_venda = custo_total / margem_venda

        produto = Produto(
            nome=nome,
            equipamento_id=equipamento_id,
            material_id=material_id,
            tempo_producao=tempo_producao,
            quantidade_material=quantidade_material,
            energia=energia,
            material_custo=material_custo,
            custo_total=custo_total,
            preco_promocional=preco_promocional,
            preco_venda=preco_venda,
            material_nome=material.nome,
            material_fabricante=material.fabricante,
            material_cor=material.cor
        )

        db.session.add(produto)
        db.session.commit()
        return redirect("/produtos")

    return render_template(
        "produtos.html",
        produtos=produtos,
        equipamentos=equipamentos,
        materiais=materiais,
        margem_promocional=margem_promocional,
        margem_venda=margem_venda
    )


@app.route("/produtos/deletar/<int:id>", methods=["POST"])
def deletar_produto(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect("/produtos")

# ---------------- Produzir Produto ----------------
@app.route("/produtos/produzir/<int:id>", methods=["POST"])
def produzir_produto(id):
    produto = Produto.query.get_or_404(id)
    material = ItemAlmoxarifado.query.get_or_404(produto.material_id)

    # 1. validar estoque
    if material.quantidade < produto.quantidade_material:
        return redirect("/produtos")

    # 2. descontar material do almoxarifado
    material.quantidade -= produto.quantidade_material

    # 3. procurar se já existe em Produzido
    produzido = Produzido.query.filter_by(produto_id=produto.id).first()

    if produzido:
        produzido.quantidade += 1
        produzido.valor_total_estoque = produzido.quantidade * produzido.custo_unitario
        produzido.disponivel = produzido.quantidade > 0
    else:
        produzido = Produzido(
            produto_id=produto.id,
            nome=produto.nome,
            material_nome=produto.material_nome,
            material_fabricante=produto.material_fabricante,
            material_cor=produto.material_cor,
            quantidade=1,
            peso_unitario_g=produto.quantidade_material,
            tempo_unitario_horas=produto.tempo_producao,
            custo_unitario=produto.custo_total,
            valor_total_estoque=produto.custo_total,
            disponivel=True
        )
        db.session.add(produzido)

    db.session.commit()
    return redirect("/financeiro?aba=produzidos")

# ---------------- FINANCEIRO ----------------

@app.route("/financeiro")
def financeiro():
    aba = request.args.get("aba", "produzidos")

    produzidos = Produzido.query.order_by(Produzido.nome.asc()).all()
    vendidos = Vendido.query.order_by(Vendido.nome.asc()).all()
    reaproveitamentos = Reaproveitamento.query.order_by(Reaproveitamento.id.asc()).all()

    itens_almoxarifado = ItemAlmoxarifado.query.all()

    valor_almoxarifado_manutencao = sum(
        (i.quantidade or 0) * (i.custo_unitario or 0)
        for i in itens_almoxarifado
        if i.categoria == "manutencao" and i.unidade == "un"
    )

    valor_almoxarifado_materiais = sum(
        (i.quantidade or 0) * ((i.custo_unitario or 0) / 1000)
        for i in itens_almoxarifado
        if i.categoria == "material"
    )

    valor_total_almoxarifado = valor_almoxarifado_materiais + valor_almoxarifado_manutencao
    valor_produzidos = sum((p.valor_total_estoque or 0) for p in produzidos)
    faturamento_total = sum((v.valor_venda_total or 0) for v in vendidos)
    lucro_total = sum((v.lucro_total or 0) for v in vendidos)
    valor_reaproveitamento = sum((r.valor_total or 0) for r in reaproveitamentos)

        # ---------------- MATERIAIS BASE DO REAPROVEITAMENTO ----------------
    materiais_base = [
        i for i in itens_almoxarifado
        if i.categoria == "material" 
    ]

    catalogo_reaproveitamento = []

    for m in materiais_base:
        registros = [
            r for r in reaproveitamentos
            if r.categoria_item == "material"
            and r.material_nome == m.nome
            and (r.material_cor or "") == (m.cor or "")
            and (r.material_fabricante or "") == (m.fabricante or "")
        ]

        qtd_peca_rejeitada = sum((r.quantidade or 0) for r in registros if r.motivo == "peca_rejeitada")
        qtd_suporte = sum((r.quantidade or 0) for r in registros if r.motivo == "suporte")
        qtd_descarte = sum((r.quantidade or 0) for r in registros if r.motivo == "descarte")

        valor_peca_rejeitada = sum((r.valor_total or 0) for r in registros if r.motivo == "peca_rejeitada")
        valor_suporte = sum((r.valor_total or 0) for r in registros if r.motivo == "suporte")
        valor_descarte = sum((r.valor_total or 0) for r in registros if r.motivo == "descarte")

        tempo_gasto_reais = sum((r.tempo_gasto_reais or 0) for r in registros)

        if registros:
            valor_unitario = registros[0].valor_unitario or 0.0
        else:
            valor_unitario = (m.custo_unitario or 0.0) / 1000

        qtd_total = qtd_peca_rejeitada + qtd_suporte + qtd_descarte
        valor_total = valor_peca_rejeitada + valor_suporte + valor_descarte

        catalogo_reaproveitamento.append({
            "material_nome": m.nome,
            "material_cor": m.cor or "",
            "material_fabricante": m.fabricante or "",

            "qtd_peca_rejeitada": qtd_peca_rejeitada,
            "qtd_suporte": qtd_suporte,
            "qtd_descarte": qtd_descarte,
            "qtd_total": qtd_total,

            "valor_peca_rejeitada": valor_peca_rejeitada,
            "valor_suporte": valor_suporte,
            "valor_descarte": valor_descarte,
            "valor_total": valor_total,

            "valor_unitario": valor_unitario,
            "tempo_gasto_reais": tempo_gasto_reais,
            "material_gasto_reais": valor_total
        })

    # ---------------- ITENS DE MANUTENÇÃO NO REAPROVEITAMENTO ----------------
    reaproveitamento_manutencao = [
        r for r in reaproveitamentos
        if r.categoria_item == "manutencao"
    ]

    materiais_almox = [
        i for i in itens_almoxarifado
        if i.categoria == "material"
    ]

    itens_manutencao_almox = [
        i for i in itens_almoxarifado
        if i.categoria == "manutencao"
    ]

    return render_template(
        "financeiro.html",
        aba=aba,
        produzidos=produzidos,
        vendidos=vendidos,
        reaproveitamentos=reaproveitamentos,
        catalogo_reaproveitamento=catalogo_reaproveitamento,
        reaproveitamento_manutencao=reaproveitamento_manutencao,
        valor_almoxarifado_materiais=valor_almoxarifado_materiais,
        valor_almoxarifado_manutencao=valor_almoxarifado_manutencao,
        valor_total_almoxarifado=valor_total_almoxarifado,
        valor_produzidos=valor_produzidos,
        faturamento_total=faturamento_total,
        lucro_total=lucro_total,
        valor_reaproveitamento=valor_reaproveitamento,
        materiais_almox=materiais_almox,
        itens_manutencao_almox=itens_manutencao_almox,
    )


# ---------------- PRODUZIDOS -> EXCLUIR ----------------
@app.route("/financeiro/produzidos/excluir/<int:id>", methods=["POST"])
def excluir_produzido(id):
    produzido = Produzido.query.get_or_404(id)
    produto = Produto.query.get_or_404(produzido.produto_id)

    if produzido.quantidade > 0:
        quantidade_total_g = produzido.quantidade * produzido.peso_unitario_g

        valor_material_g = 0.0
        if produto.quantidade_material and produto.quantidade_material > 0:
            valor_material_g = (produto.material_custo or 0.0) / produto.quantidade_material

        valor_total_material = quantidade_total_g * valor_material_g
        tempo_gasto_reais = (produto.energia or 0.0) * produzido.quantidade

        reap = Reaproveitamento.query.filter_by(
            categoria_item="material",
            material_nome=produto.material_nome,
            material_cor=produto.material_cor,
            material_fabricante=produto.material_fabricante,
            motivo="descarte",
            origem="produzidos",
            unidade="g"
        ).first()

        if reap:
            reap.quantidade += quantidade_total_g
            reap.valor_total += valor_total_material
            reap.tempo_gasto_reais += tempo_gasto_reais
        else:
            reap = Reaproveitamento(
                produto_id=produto.id,
                categoria_item="material",
                material_nome=produto.material_nome,
                material_cor=produto.material_cor,
                material_fabricante=produto.material_fabricante,
                unidade="g",
                motivo="descarte",
                quantidade=quantidade_total_g,
                valor_unitario=valor_material_g,
                valor_total=valor_total_material,
                tempo_gasto_reais=tempo_gasto_reais,
                origem="produzidos"
            )
            db.session.add(reap)

    db.session.delete(produzido)
    db.session.commit()

    return redirect("/financeiro?aba=produzidos")


# ---------------- PRODUZIDOS -> VENDIDO ----------------
@app.route("/financeiro/produzidos/vender/<int:id>", methods=["POST"])
def vender_produzido(id):
    produzido = Produzido.query.get_or_404(id)
    produto = Produto.query.get_or_404(produzido.produto_id)

    if produzido.quantidade <= 0:
        return redirect("/financeiro?aba=produzidos")

    valor_venda_unitario = float(produto.preco_venda or 0.0)
    custo_unitario = float(produzido.custo_unitario or 0.0)

    vendido = Vendido.query.filter_by(produto_id=produto.id).first()

    if vendido is None:
        vendido = Vendido(
            produto_id=produto.id,
            nome=produto.nome,
            material_nome=produto.material_nome,
            material_cor=produto.material_cor,
            quantidade=0,
            valor_venda_unitario=0.0,
            valor_venda_total=0.0,
            custo_unitario=0.0,
            custo_total=0.0,
            lucro_total=0.0
        )
        db.session.add(vendido)

    # atualiza vendidos
    vendido.quantidade += 1
    vendido.valor_venda_unitario = valor_venda_unitario
    vendido.valor_venda_total = vendido.quantidade * vendido.valor_venda_unitario
    vendido.custo_unitario = custo_unitario
    vendido.custo_total = vendido.quantidade * vendido.custo_unitario
    vendido.lucro_total = vendido.valor_venda_total - vendido.custo_total

    # baixa em produzidos
    produzido.quantidade -= 1
    produzido.valor_total_estoque = produzido.quantidade * produzido.custo_unitario
    produzido.disponivel = produzido.quantidade > 0
    print("VENDIDO:", vendido.nome, vendido.quantidade, vendido.valor_venda_total)
    db.session.commit()

    return redirect("/financeiro?aba=vendidos")


# ---------------- PRODUZIDOS -> REAPROVEITAR ----------------
@app.route("/financeiro/produzidos/reaproveitar/<int:id>", methods=["POST"])
def reaproveitar_produzido(id):
    produzido = Produzido.query.get_or_404(id)
    produto = Produto.query.get_or_404(produzido.produto_id)

    if produzido.quantidade <= 0:
        return redirect("/financeiro?aba=produzidos")

    # baixa 1 unidade em Produzidos
    produzido.quantidade -= 1
    produzido.valor_total_estoque = produzido.quantidade * produzido.custo_unitario
    produzido.disponivel = produzido.quantidade > 0

    quantidade_material = produzido.peso_unitario_g or 0.0

    # valor do material por g (não o custo total da peça)
    valor_material_g = 0.0
    if produto.quantidade_material and produto.quantidade_material > 0:
        valor_material_g = (produto.material_custo or 0.0) / produto.quantidade_material

    valor_total_material = quantidade_material * valor_material_g

    # tudo que não é material entra como "tempo gasto em R$"
    tempo_gasto_reais = produto.energia or 0.0

    reap = Reaproveitamento.query.filter_by(
        categoria_item="material",
        material_nome=produto.material_nome,
        material_cor=produto.material_cor,
        material_fabricante=produto.material_fabricante,
        motivo="peca_rejeitada",
        origem="produzidos",
        unidade="g"
    ).first()

    if reap:
        reap.quantidade += quantidade_material
        reap.valor_total += valor_total_material
        reap.tempo_gasto_reais += tempo_gasto_reais
    else:
            reap = Reaproveitamento(
            produto_id=produto.id,
            categoria_item="material",
            material_nome=produto.material_nome,
            material_cor=produto.material_cor,
            material_fabricante=produto.material_fabricante,
            unidade="g",
            motivo="peca_rejeitada",
            quantidade=quantidade_material,
            valor_unitario=valor_material_g,
            valor_total=valor_total_material,
            tempo_gasto_reais=tempo_gasto_reais,
            origem="produzidos"
        )
    db.session.add(reap)

    db.session.commit()
    return redirect("/financeiro?aba=reaproveitamento")


# ---------------- reciclar ----------------
@app.route("/financeiro/reaproveitamento/reciclar-agrupado", methods=["POST"])
def reciclar_reaproveitamento_agrupado():
    material_nome = (request.form.get("material_nome") or "").strip()
    material_cor = (request.form.get("material_cor") or "").strip()
    material_fabricante = (request.form.get("material_fabricante") or "").strip()
    quantidade_material = to_float(request.form.get("quantidade_material"))
    valor_unitario = to_float(request.form.get("valor_unitario"))

    print("RECICLAR AGRUPADO:", {
        "material_nome": material_nome,
        "material_cor": material_cor,
        "material_fabricante": material_fabricante,
        "quantidade_material": quantidade_material,
        "valor_unitario": valor_unitario
    })

    if not material_nome or quantidade_material <= 0:
        return redirect("/financeiro?aba=reaproveitamento")

    registros = Reaproveitamento.query.filter_by(
        categoria_item="material",
        material_nome=material_nome,
        material_cor=material_cor,
        material_fabricante=material_fabricante,
        unidade="g"
    ).all()

    total_disponivel = sum((r.quantidade or 0) for r in registros)

    if total_disponivel <= 0:
        return redirect("/financeiro?aba=reaproveitamento")

    if quantidade_material > total_disponivel:
        quantidade_material = total_disponivel

    nome_reaproveitado = f"{material_nome} | ({material_cor}) Reaproveitado"

    item_almox = ItemAlmoxarifado.query.filter_by(
        nome=nome_reaproveitado,
        fabricante=material_fabricante,
        cor=material_cor,
        categoria="material",
        unidade="g"
    ).first()

    custo_por_kg = valor_unitario * 1000

    if item_almox:
        item_almox.quantidade = (item_almox.quantidade or 0) + quantidade_material
        item_almox.custo_unitario = custo_por_kg
    else:
        item_almox = ItemAlmoxarifado(
            nome=nome_reaproveitado,
            fabricante=material_fabricante,
            cor=material_cor,
            categoria="material",
            unidade="g",
            quantidade=quantidade_material,
            custo_unitario=custo_por_kg
        )
        db.session.add(item_almox)

    restante = quantidade_material

    for r in registros:
        if restante <= 0:
            break

        qtd_registro = r.quantidade or 0

        if qtd_registro <= restante:
            restante -= qtd_registro
            db.session.delete(r)
        else:
            r.quantidade = qtd_registro - restante
            r.valor_total = (r.quantidade or 0) * (r.valor_unitario or 0)
            restante = 0

    db.session.commit()
    return redirect("/financeiro?aba=reaproveitamento")

# ---------------- Adicionar ----------------
@app.route("/financeiro/reaproveitamento/adicionar", methods=["POST"])
def adicionar_reaproveitamento_manual():
    categoria_item = request.form.get("categoria_item")
    motivo = request.form.get("motivo")

    if categoria_item == "material":
        item_id = to_int(request.form.get("material_id"))
        quantidade = to_float(request.form.get("quantidade_material"))

        item = ItemAlmoxarifado.query.get_or_404(item_id)

        if quantidade <= 0:
            return redirect("/financeiro?aba=reaproveitamento")

        valor_unitario_g = (item.custo_unitario or 0.0) / 1000
        valor_total = quantidade * valor_unitario_g

        reap = Reaproveitamento.query.filter_by(
            categoria_item="material",
            material_nome=item.nome,
            material_cor=item.cor,
            material_fabricante=item.fabricante,
            motivo=motivo,
            origem="manual",
            unidade="g"
        ).first()

        if reap:
            reap.quantidade += quantidade
            reap.valor_total += valor_total
        else:
            reap = Reaproveitamento(
                categoria_item="material",
                material_nome=item.nome,
                material_cor=item.cor,
                material_fabricante=item.fabricante,
                unidade="g",
                motivo=motivo,
                quantidade=quantidade,
                valor_unitario=valor_unitario_g,
                valor_total=valor_total,
                tempo_gasto_reais=0.0,
                origem="manual"
            )
            db.session.add(reap)

    elif categoria_item == "manutencao":
        item_id = to_int(request.form.get("item_manutencao_id"))
        quantidade = to_float(request.form.get("quantidade_item"))

        item = ItemAlmoxarifado.query.get_or_404(item_id)

        if quantidade <= 0:
            return redirect("/financeiro?aba=reaproveitamento")

        if item.unidade == "g":
            valor_unitario = (item.custo_unitario or 0.0) / 1000
        else:
            valor_unitario = item.custo_unitario or 0.0

        valor_total = quantidade * valor_unitario

        reap = Reaproveitamento.query.filter_by(
            categoria_item="manutencao",
            item_nome=item.nome,
            motivo=motivo,
            origem="manual",
            unidade=item.unidade
        ).first()

        if reap:
            reap.quantidade += quantidade
            reap.valor_total += valor_total
        else:
            reap = Reaproveitamento(
                categoria_item="manutencao",
                item_nome=item.nome,
                unidade=item.unidade,
                motivo=motivo,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total=valor_total,
                tempo_gasto_reais=0.0,
                origem="manual"
            )
            db.session.add(reap)

    db.session.commit()
    return redirect("/financeiro?aba=reaproveitamento")

# ---------------- Excluir reaproveitamento ----------------
@app.route("/financeiro/reaproveitamento/excluir/<int:id>", methods=["POST"])
def excluir_reaproveitamento(id):
    reap = Reaproveitamento.query.get_or_404(id)
    db.session.delete(reap)
    db.session.commit()
    return redirect("/financeiro?aba=reaproveitamento")

# ---------------- START ----------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    print(">>> INICIANDO SERVIDOR FLASK <<<")
    app.run(debug=True, use_reloader=False)