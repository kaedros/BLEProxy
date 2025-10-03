#
# Proposito: Conectar-se a um dispositivo BLE, enviar um comando de inicializacao
# para uma Caracteristica de Controle e, em seguida, habilitar e monitorar
# notificacoes de uma Caracteristica de Dados.
#
# Requer o endereco, o UUID da Caracteristica de Notificacao e, opcionalmente,
# o UUID e o valor para a Caracteristica de Comando (WRITE).
#
# >python.exe .\enNotification.py FE:98:00:30:39:44 ff01 --control-uuid ff01 --control-value 020106030209181716
# >python.exe .\enNotification.py FE:98:00:30:39:44 fff3 --control-uuid fff3 --control-value AA5501

import asyncio
import argparse
from bleak import BleakClient
from bleak.exc import BleakError

# Dicionario para mapeamento de UUIDs
UUID_DESCRIPTIONS = {
    "0000180D": "Heart Rate Service",
    "00002A37": "Heart Rate Measurement",
    "00002A19": "Battery Level",
    "00002902": "Client Characteristic Configuration Descriptor (CCCD)",
    # Adicionando o UUID FF01 para contexto
    "0000FF01": "Caracteristica Proprietaria (Controle/Dados)",
}

def get_uuid_description(uuid_str: str) -> str:
    """Busca a descricao padrao para um UUID de 128-bit."""
    normalized_uuid = str(uuid_str).upper().replace('-', '')
    BASE_UUID_SUFFIX = '00001000800000805F9B34FB'
    
    if normalized_uuid.endswith(BASE_UUID_SUFFIX):
        search_key = normalized_uuid[:8] 
        return UUID_DESCRIPTIONS.get(search_key, "UUID Padrao")
    
    # Verifica UUIDs customizados curtos como 'FF01'
    return UUID_DESCRIPTIONS.get(normalized_uuid[4:8], "UUID Customizado")


def notification_handler(characteristic_uuid: str, data: bytearray):
    """Callback chamado sempre que uma notificacao e recebida."""
    uuid_desc = get_uuid_description(characteristic_uuid)
    hex_data = data.hex().upper()
    
    try:
        string_value = data.decode('utf-8', errors='ignore').strip()
        # Filtra caracteres nao imprimiveis
        if string_value and all(32 <= ord(c) <= 126 or ord(c) in (9, 10, 13) for c in string_value):
            valor_formatado = f"'{string_value}'"
        else:
            valor_formatado = f"Dados ({len(data)} bytes)"
    except Exception:
        valor_formatado = f"Dados ({len(data)} bytes)"
    
    print(f"\n[RECEIVED DATA @ {asyncio.get_event_loop().time():.2f}s] <------------------")
    print(f"  → Notificacao de: {uuid_desc} ({characteristic_uuid})")
    print(f"  → Valor: {valor_formatado} | Hex: [{hex_data}]")
    print("----------------------------------------------------------------")


async def run_sequence(address: str, control_uuid: str, control_value_hex: str, notify_uuid: str, timeout: float):
    """Executa a sequencia de comando de escrita e ativacao de notificacao com a ordem CORRIGIDA."""
    print(f"📡 Tentando conectar ao dispositivo em: {address}...")
    
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                print("❌ Falha ao conectar.")
                return

            print("✅ Conectado com sucesso!\n")

            # --- 1. HABILITAR NOTIFICACAO (PRIMEIRO) ---
            print(f"\n🔬 Caracteristica de Notificacao alvo: {notify_uuid} ({get_uuid_description(notify_uuid)})")
            
            char = client.services.get_characteristic(notify_uuid)
            if not char or not any(prop in char.properties for prop in ['notify', 'indicate']):
                print(f"❌ Erro: Caracteristica {notify_uuid} nao suporta notificacao/indicacao.")
                return

            # A BLEAK ESCREVE 0x0100 NO CCCD AQUI, ATIVANDO O CANAL DE RECEBIMENTO.
            print(f"🔔 Habilitando notificacoes (escrita automatica no CCCD 0x2902)...")
            await client.start_notify(notify_uuid, notification_handler)
            print("✅ Notificacoes Habilitadas.")


            # --- 2. ENVIAR COMANDO DE INICIALIZACAO (SEGUNDO) ---
            if control_uuid and control_value_hex:
                # O comando so e enviado se os argumentos '--control-uuid' e '--control-value' forem fornecidos.
                print(f"\n➡️ Tentando escrever comando de controle na Caracteristica ({control_uuid})...")
                
                try:
                    # Converte a string HEX para bytes
                    control_value_bytes = bytes.fromhex(control_value_hex)
                    
                    # Usa response=False para ser consistente com o teste bem-sucedido
                    await client.write_gatt_char(control_uuid, control_value_bytes, response=False)
                    print(f"✅ Comando de ativacao ('{control_value_hex}') enviado com sucesso!")
                except Exception as e:
                    print(f"❌ Erro ao escrever na Caracteristica de Controle ({control_uuid}): {e}")
            
            # 3. Espera pelo tempo de execucao
            print(f"\n⏳ Monitorando dados por {timeout:.0f} segundos (ou ate Ctrl+C).\n")
            await asyncio.sleep(timeout)

            # 4. Desabilita a inscricao
            print("\n🛑 Tempo esgotado. Desabilitando notificacoes...")
            await client.stop_notify(notify_uuid)
            
            print("✅ Monitoramento concluido.")

    except BleakError as e:
        print(f"\n❌ Erro de conexao ou BLE: {e}")
    except Exception as e:
        print(f"\n❌ Ocorreu um erro inesperado: {type(e).__name__}: {e}")

# --- Funcoes Principais ---

def main():
    """Configura e executa a logica principal."""
    parser = argparse.ArgumentParser(
        description="Conecta a um dispositivo BLE, envia um comando de inicializacao e monitora notificacoes."
    )
    parser.add_argument(
        'address',
        type=str,
        help="O endereco MAC (Bluetooth Address) do dispositivo alvo (ex: 'AA:BB:CC:DD:EE:FF')."
    )
    parser.add_argument(
        'notify_uuid',
        type=str,
        help="O UUID da Caracteristica de Notificacao (dados que voce deseja receber)."
    )
    parser.add_argument(
        '--control-uuid',
        type=str,
        default=None,
        help="[OPCIONAL] O UUID da Caracteristica de Controle (WRITE) para enviar o comando de inicializacao."
    )
    parser.add_argument(
        '--control-value',
        type=str,
        default=None,
        help="[OPCIONAL] O valor HEX do comando de inicializacao a ser escrito (ex: '020106030209181716')."
    )
    parser.add_argument(
        '-t', '--timeout',
        type=float,
        default=10.0,
        help="Duracao do monitoramento em segundos (padrao: 10.0)."
    )
    
    args = parser.parse_args()

    # Valida se o comando de controle foi especificado de forma completa
    if (args.control_uuid and not args.control_value) or (not args.control_uuid and args.control_value):
        print("\n❌ ERRO: Para enviar um comando de controle, voce deve fornecer AMBOS --control-uuid E --control-value.")
        parser.print_help()
        return

    # Inicia a execucao assincrona
    asyncio.run(run_sequence(
        args.address, 
        args.control_uuid, 
        args.control_value, 
        args.notify_uuid, 
        args.timeout
    ))

if __name__ == "__main__":
    main()
