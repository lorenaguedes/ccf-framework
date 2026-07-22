"""
Modulo de estimativa de idade facial - Estagio E3 (RF05, Tabela 12,
PGT).

Classifica indivíduos em imagens quanto a faixa etaria MENOR/ADULTO,
usando o modelo MiVOLO (Kuprashevich & Tolstykh, 2023) como preditor
de idade, aplicado apos a deteccao de conteudo explicito (E2).

Referencia: MiVOLO superou o fine-tuning proprio de ResNet50/ImageNet
em teste comparativo documentado nesta sessao (recall MENOR: 86,51%
vs 82,54%), justificando sua adocao como preditor principal do E3.

Estrategia de design: mesma injecao de dependencia dos demais modulos
de IA - predict_fn sintetica para testes unitarios, MiVOLO real via
create_mivolo_predict_fn (validado manualmente, nao coberto por testes
automatizados).
"""
from typing import Callable


def classify_age(
    image,
    predict_fn: Callable,
    threshold: float = 18,
) -> dict:
    """Classifica uma imagem quanto a faixa etaria MENOR/ADULTO, com
    base na idade estimada por uma funcao de predicao externa (ex:
    MiVOLO).

    Args:
        image: imagem de entrada (formato aceito depende da predict_fn).
        predict_fn: funcao que recebe a imagem e retorna a idade
            estimada (float, em anos).
        threshold: idade limite (anos). Idades estritamente menores
            que o threshold sao classificadas como MENOR; o proprio
            valor do threshold (ex: exatos 18 anos) e classificado
            como ADULTO - decisao alinhada ao criterio juridico de
            maioridade (ECA: menor e quem tem MENOS de 18 anos
            completos).

    Returns:
        Dicionario com:
        - idade_estimada: valor retornado pelo modelo (anos)
        - flag: "MENOR" ou "ADULTO"

    Raises:
        ValueError: se a idade estimada for negativa - fisicamente
            impossivel, indica falha do modelo, nao deve ser
            silenciada.
    """
    idade_estimada = predict_fn(image)

    if idade_estimada < 0:
        raise ValueError(
            f"Idade estimada invalida: {idade_estimada}. "
            "Valores negativos indicam falha do modelo de predicao."
        )

    flag = "MENOR" if idade_estimada < threshold else "ADULTO"

    return {
        "idade_estimada": idade_estimada,
        "flag": flag,
    }


def create_mivolo_predict_fn() -> Callable:  # pragma: no cover
    """Cria a funcao de predicao real usando o modelo MiVOLO
    (iitolstykh/mivolo_v2, Hugging Face), para uso em producao.

    Nota: excluida da cobertura de testes unitarios propositalmente -
    depende do download e inferencia real do MiVOLO (~115MB via HF
    Hub), validada manualmente no Colab (ver notebook
    E2_visao_computacional_cnn.ipynb, celulas 19-26) com resultado de
    recall MENOR = 86,51% no conjunto de teste UTKFace.

    Returns:
        Funcao compativel com classify_age, que recebe uma imagem
        (array numpy RGB, formato de rosto ja recortado, compativel
        com UTKFace) e retorna a idade estimada real.
    """
    import torch
    from transformers import AutoConfig, AutoImageProcessor, AutoModelForImageClassification

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    config = AutoConfig.from_pretrained("iitolstykh/mivolo_v2", trust_remote_code=True)
    modelo = AutoModelForImageClassification.from_pretrained(
        "iitolstykh/mivolo_v2", trust_remote_code=True, torch_dtype=torch.float32
    ).to(device)
    image_processor = AutoImageProcessor.from_pretrained("iitolstykh/mivolo_v2", trust_remote_code=True)

    def predict_fn(image) -> float:
        proc = image_processor.preprocess(images=[image])
        pixel_vals = proc["pixel_values"].to(device, dtype=torch.float32)
        corpo_vazio = torch.zeros_like(pixel_vals)

        with torch.no_grad():
            saida = modelo(faces_input=pixel_vals, body_input=corpo_vazio)

        return saida.age_output.item()

    return predict_fn