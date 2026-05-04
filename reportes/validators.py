"""
Validadores de payloads para endpoints de reportes
ASR Integridad: Validación de esquemas JSON
"""
try:
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    ValidationError = Exception


SCHEMA_REPORTE_COSTOS = {
    "type": "object",
    "required": ["mes", "ano"],
    "properties": {
        "mes": {
            "type": "integer",
            "minimum": 1,
            "maximum": 12,
            "description": "Mes del reporte (1-12)"
        },
        "ano": {
            "type": "integer",
            "minimum": 2020,
            "maximum": 2099,
            "description": "Año del reporte"
        },
        "incluir_detalle": {
            "type": "boolean",
            "default": False,
            "description": "Incluir detalles en el reporte"
        },
        "filtros": {
            "type": "object",
            "description": "Filtros adicionales",
            "properties": {
                "proveedor": {
                    "type": "string",
                    "enum": ["AWS", "GCP"],
                    "description": "Proveedor cloud"
                },
                "proyecto": {
                    "type": "string",
                    "description": "Nombre del proyecto"
                }
            }
        }
    },
    "additionalProperties": False  # Rechaza campos desconocidos
}


class PayloadValidator:
    """Validador de payloads JSON contra esquemas"""
    
    @staticmethod
    def validar_reporte_costos(data):
        """
        Valida que el payload cumpla con el schema esperado para reportes de costos.
        
        Lanza ValidationError si no es válido.
        
        Args:
            data (dict): Payload a validar
            
        Returns:
            bool: True si es válido
            
        Raises:
            ValidationError: Si el payload no cumple con el schema
        """
        if not HAS_JSONSCHEMA:
            # STUB: Sin jsonschema instalado, hacer validación básica
            if not isinstance(data, dict):
                raise ValidationError("Payload debe ser un diccionario")
            if 'mes' not in data or 'ano' not in data:
                raise ValidationError("Parámetros mes y ano requeridos")
            if not (1 <= int(data.get('mes', 0)) <= 12):
                raise ValidationError("mes debe estar entre 1-12")
            return True
        
        # Con jsonschema: validar contra schema completo
        validate(instance=data, schema=SCHEMA_REPORTE_COSTOS)
        return True
