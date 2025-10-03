#
# Proposito: Conectar-se a um dispositivo Bluetooth Low Energy (BLE)
# especificado pelo seu endereco MAC/Address, e listar todos os Servicos e
# Caracteristicas. Tenta ler o valor de cada caracteristica de leitura disponivel
# e decodifica para string se possivel.
#
# Requerimentos: O endereco MAC/Address deve ser fornecido como argumento.
#
import asyncio
import argparse
from bleak import BleakClient
from bleak.exc import BleakError

# --- Mapeamento de UUIDs Padrao (Bluetooth SIG) ---
UUID_DESCRIPTIONS = {
    # Servicos Comuns (0x18xx)
    "0000180F": "Battery Service",
    "0000180A": "Device Information Service",
    "0000180D": "Heart Rate Service",
    "00001800": "Generic Access Service",
    "00001801": "Generic Attribute Service",
    "0000181A": "Environmental Sensing Service",
    
    # Caracteristicas Comuns (0x2Axx)
    "00002A00": "Device Name",
    "00002A01": "Appearance",
    "00002A05": "Service Changed",
    "00002A19": "Battery Level",
    "00002A29": "Manufacturer Name String",
    "00002A24": "Model Number String",
    "00002A25": "Serial Number String",
    "00002A37": "Heart Rate Measurement",
    "00002A2B": "Current Time",
    "00002A50": "PnP ID (Product ID)",

    # Descritores Comuns
    "00002902": "Client Characteristic Configuration Descriptor (CCCD)",
}

def get_uuid_description(uuid_str: str) -> str:
    """Busca a descricao padrao para um UUID de 128-bit, se for um UUID SIG de 16-bit."""
    normalized_uuid = uuid_str.upper().replace('-', '')
    BASE_UUID_SUFFIX = '00001000800000805F9B34FB'
    
    if normalized_uuid.endswith(BASE_UUID_SUFFIX):
        search_key = normalized_uuid[:8] 
        return UUID_DESCRIPTIONS.get(search_key, "UUID Padrao (Descricao Desconhecida)")
    
    return "UUID Customizado"

def decode_value(value: bytes) -> str:
    """Tenta decodificar um valor bytes para uma string e retorna a formatacao desejada."""
    hex_value = value.hex().upper()
    try:
        # Tenta decodificar usando UTF-8 (comum para strings de texto BLE)
        string_value = value.decode('utf-8', errors='ignore').strip()
        
        # Filtra caracteres nao imprimiveis e retorna o formato String [Hex]
        if string_value and all(32 <= ord(c) <= 126 or ord(c) in (9, 10, 13) for c in string_value):
            return f"'{string_value}' [0x{hex_value}] Hex"
        
        # Se for decodificavel, mas nao parece ser texto simples
        return f"Dados Binarios/Numericos [0x{hex_value}] Hex"
        
    except UnicodeDecodeError:
        # Se falhar na decodificacao (dados binarios puros, numeros, etc.)
        return f"Dados Binarios/Numericos [0x{hex_value}] Hex"
    except Exception:
        # Qualquer outro erro
        return f"Erro ao formatar [0x{hex_value}] Hex"


async def list_services_and_chars(address: str):
    """Tenta conectar ao dispositivo e lista seus servicos, caracteristicas e tenta ler o valor."""
    print(f"📡 Tentando conectar ao dispositivo em: {address}...")
    
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                print("❌ Falha ao conectar. Verifique se o endereco esta correto e o dispositivo esta proximo.")
                return

            print("✅ Conectado com sucesso!\n")
            print("📋 Servicos e Caracteristicas disponiveis:\n")

            for service in client.services:
                service_uuid_str = str(service.uuid)
                service_desc = get_uuid_description(service_uuid_str)
                
                print(f"→ SERVICO: {service_uuid_str}")
                print(f"  Descricao: {service_desc}")
                print(f"  Handle: 0x{service.handle:04X}")
                
                for char in service.characteristics:
                    properties = ", ".join(char.properties)
                    char_uuid_str = str(char.uuid)
                    char_desc = get_uuid_description(char_uuid_str)
                    
                    readable = "✓" if "read" in char.properties else "✗"
                    writable = "✓" if "write" in char.properties else "✗"
                    notify = "✓" if "notify" in char.properties else "✗"

                    value_display = "N/A"
                    if "read" in char.properties:
                        try:
                            value_bytes = await client.read_gatt_char(char.uuid)
                            # --- NOVO: Decodificacao e formatacao ---
                            value_display = decode_value(value_bytes)
                        except Exception as e:
                            value_display = f"Erro ao ler ({type(e).__name__})"

                    print(f"  → CARACTERISTICA: {char_uuid_str}")
                    print(f"    Descricao: {char_desc}")
                    print(f"    Propriedades: [{properties}]")
                    print(f"    Leitura: {readable} | Escrita: {writable} | Notificacao: {notify}")
                    print(f"    Valor Lido: {value_display}")
                    
                    for descriptor in char.descriptors:
                        desc_uuid_str = str(descriptor.uuid)
                        desc_desc = get_uuid_description(desc_uuid_str)
                        print(f"    - Descritor: {desc_uuid_str}")
                        print(f"      Descricao: {desc_desc} | Handle: 0x{descriptor.handle:04X}")

                print("\n" + "=" * 100)
        
        print(f"\n✅ Analise de servicos concluida para {address}.")

    except BleakError as e:
        print(f"\n❌ Erro de conexao ou BLE: {e}")
        print("Dica: Certifique-se de que o dispositivo esta ligado/anunciando e o endereco esta correto.")
    except Exception as e:
        print(f"\n❌ Ocorreu um erro inesperado: {type(e).__name__}: {e}")

# --- Funcoes Principais ---

def main():
    """Configura e executa a logica principal."""
    parser = argparse.ArgumentParser(
        description="Conecta a um dispositivo BLE pelo endereco MAC/Address e lista seus servicos e caracteristicas."
    )
    parser.add_argument(
        'address',
        type=str,
        help="O endereco MAC (Bluetooth Address) do dispositivo alvo (ex: 'AA:BB:CC:DD:EE:FF')."
    )
    
    args = parser.parse_args()

    # Inicia a execucao assincrona
    asyncio.run(list_services_and_chars(args.address))

if __name__ == "__main__":
    main()