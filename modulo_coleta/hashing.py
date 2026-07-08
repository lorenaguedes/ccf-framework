"""
Módulo de hashing forense — CCF Framework.

Calcula hashes criptográficos (SHA-256, MD5) de evidências digitais no
momento da coleta, atendendo ao RNF01 (Tabela 11, PGT): "Toda evidência
coletada deve ter seu hash SHA-256 calculado no momento da coleta e
verificável a qualquer tempo pela blockchain."

Referência normativa: ISO/IEC 27037:2012 — preservação da integridade
da evidência digital desde o momento da identificação/coleta.
"""
import hashlib


def calculate_sha256(content: bytes) -> str:
    """Calcula o hash SHA-256 de um conteúdo em bytes.

    SHA-256 é o algoritmo primário de integridade do framework (RNF01),
    por sua robustez criptográfica e ausência de colisões conhecidas
    (diferente do MD5, mantido apenas por compatibilidade legada).

    Args:
        content: conteúdo bruto da evidência, em bytes.

    Returns:
        Hash SHA-256 em formato hexadecimal (64 caracteres).
    """
    return hashlib.sha256(content).hexdigest()


def calculate_md5(content: bytes) -> str:
    """Calcula o hash MD5 de um conteúdo em bytes.

    Mantido por compatibilidade com ferramentas forenses legadas
    (Tabela 14, PGT), NÃO deve ser usado como garantia primária de
    integridade — apenas como campo auxiliar de referência cruzada.

    Args:
        content: conteúdo bruto da evidência, em bytes.

    Returns:
        Hash MD5 em formato hexadecimal (32 caracteres).
    """
    return hashlib.md5(content).hexdigest()


def calculate_hashes(content: bytes) -> dict[str, str]:
    """Calcula SHA-256 e MD5 de uma só vez, no formato usado pelo
    registro de evidência no momento da coleta.

    Args:
        content: conteúdo bruto da evidência, em bytes.

    Returns:
        Dicionário com as chaves 'sha256' e 'md5'.

    Raises:
        ValueError: se o conteúdo for vazio — evidência vazia indica
            falha na coleta, não um caso válido de hashing.
    """
    if not content:
        raise ValueError(
            "Conteúdo vazio não pode ser hasheado: possível falha na "
            "coleta da evidência."
        )
    return {
        "sha256": calculate_sha256(content),
        "md5": calculate_md5(content),
    }
