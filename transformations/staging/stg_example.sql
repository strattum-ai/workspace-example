-- Nome: Exemplo de Staging
-- Descrição: Demonstra o formato de uma transformação de staging
-- Fonte: tabela_origem
-- Atualização: sob demanda

SELECT
    id                          AS id_externo,
    nome                        AS nome,
    email                       AS email,
    created_at                  AS criado_em,
    updated_at                  AS atualizado_em
FROM tabela_origem
WHERE deletado_em IS NULL
