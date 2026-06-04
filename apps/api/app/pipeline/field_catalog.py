from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDefinition:
    field_key: str
    group_key: str
    template_field: str
    required: bool
    validation: str


FIELD_DEFINITIONS = (
    FieldDefinition("cnpj_vitima", "dados_sinistro", "CNPJ Vitima", True, "cnpj"),
    FieldDefinition("tipo_sinistro", "dados_sinistro", "Tipo Sinistro", True, "tipo_sinistro"),
    FieldDefinition("data_evento", "dados_sinistro", "Data Evento", True, "date"),
    FieldDefinition("cidade_evento", "dados_sinistro", "Cidade Evento", True, "city"),
    FieldDefinition("uf_evento", "dados_sinistro", "UF Evento", True, "uf"),
    FieldDefinition("evento_natureza", "dados_sinistro", "Evento ou Natureza", True, "text"),
    FieldDefinition("mercadoria", "dados_sinistro", "Mercadoria", True, "text"),
    FieldDefinition("data_embarque", "dados_sinistro", "Data Embarque", True, "date"),
    FieldDefinition("cpf_motorista", "motorista", "CPF Motorista", True, "cpf"),
    FieldDefinition(
        "placa_veiculo_sinistrado",
        "veiculo_sinistrado",
        "Placa veiculo Sinistrado",
        True,
        "placa_brasil",
    ),
    FieldDefinition(
        "cidade_emplacamento",
        "veiculo_sinistrado",
        "Cidade Emplacamento",
        True,
        "city",
    ),
    FieldDefinition("uf_emplacamento", "veiculo_sinistrado", "UF Emplacamento", True, "uf"),
    FieldDefinition("numero_bo", "boletim", "Numero BO", False, "text"),
)

FIELD_DEFINITIONS_BY_KEY = {definition.field_key: definition for definition in FIELD_DEFINITIONS}
REQUIRED_FIELD_KEYS = tuple(
    definition.field_key for definition in FIELD_DEFINITIONS if definition.required
)
