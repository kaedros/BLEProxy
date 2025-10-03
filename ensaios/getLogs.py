#
# Conectar, enviar o comando de ativacao AA5501 para fff3,
# habilitar notificacoes em fff3 e imprimir os dados brutos recebidos.
# Acumula todos os dados e, ao final, decodifica a temperatura (2 bytes, Little Endian / 100).
#
# Uso: python getLogs.py FE:98:00:30:39:44
#
import asyncio
import argparse
import sys
from bleak import BleakClient
from bleak.exc import BleakError

# --- CONFIGURAÇÕES FIXAS ---
TARGET_CHAR_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"
ACTIVATION_COMMAND = b"\xAA\x55"  # Comando de ativacao (AA5501 em bytes)
TIMEOUT_S = 60.0                      # Tempo de monitoramento


async def run_raw_logger(address: str):
    """Executa a sequência de conexão, ativação, log bruto e processamento final."""
    print(f"📡 Tentando conectar ao dispositivo em: {address}...")
    
    # Variável para acumular todos os bytes recebidos
    all_data = bytearray()

    def handler(characteristic_uuid: str, data: bytearray):
        """Callback que loga e acumula os dados recebidos."""
        hex_data = data.hex().upper()
        timestamp = asyncio.get_event_loop().time()
        
        # Imprime a notificação no formato bruto (Log de recepção mantido)
        print(f"[{timestamp:.2f}s] 📥 Recebido ({len(data)} bytes): {hex_data}")
        
        # Acumula os bytes recebidos
        all_data.extend(data)

    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                print("❌ Falha ao conectar.")
                return

            print("✅ Conectado com sucesso!\n")
            print(f"🔬 Característica alvo para Notificação e Comando: {TARGET_CHAR_UUID}")

            # --- PASSO 1: HABILITAR NOTIFICAÇÃO ---
            print("🔔 Habilitando notificações...")
            await client.start_notify(TARGET_CHAR_UUID, handler)
            print("✅ Notificações Habilitadas.")


            # --- PASSO 2: ENVIAR COMANDO DE ATIVAÇÃO ---
            print(f"\n➡️ Enviando comando de ativação ({ACTIVATION_COMMAND.hex().upper()}) para {TARGET_CHAR_UUID}...")
            
            try:
                await client.write_gatt_char(TARGET_CHAR_UUID, ACTIVATION_COMMAND, response=False)
                print("✅ Comando de ativação enviado com sucesso!")
            except Exception as e:
                print(f"❌ Erro ao enviar comando de ativação: {e}")
                
            
            # --- PASSO 3: MONITORAR DADOS E ACUMULAR ---
            print(f"\n⏳ Monitorando dados por {TIMEOUT_S:.0f} segundos (ou até Ctrl+C).\n")
            await asyncio.sleep(TIMEOUT_S)

            # --- PASSO 4: DESABILITAR NOTIFICAÇÃO ---
            print("\n🛑 Tempo esgotado. Desabilitando notificações...")
            await client.stop_notify(TARGET_CHAR_UUID)
            
            print("=" * 60)
            print("✅ Monitoramento concluído.")

            # --- PASSO 5: PROCESSAMENTO E CONVERSÃO FINAL ---
            await process_accumulated_data(all_data)

    except BleakError as e:
        print(f"\n❌ Erro de conexão ou BLE: {e}")
    except Exception as e:
        print(f"\n❌ Ocorreu um erro inesperado: {type(e).__name__}: {e}")

async def process_accumulated_data(data_bytes: bytearray):
    """
    Processa todos os bytes acumulados, decodificando a temperatura a cada 2 bytes.
    Saída em formato CSV (valores separados por vírgula).
    """
    if not data_bytes:
        print("Nenhum dado recebido para processamento.")
        return

    # Aviso se o total de bytes não for múltiplo de 2
    if len(data_bytes) % 2 != 0:
        sys.stderr.write(f"\n⚠️ Aviso: O número total de bytes ({len(data_bytes)}) é ímpar. O último byte será ignorado.\n")

    temperatures = []
    
    # Itera sobre os bytes a cada 2, garantindo que haja pelo menos 2 bytes no chunk
    for i in range(0, len(data_bytes) - 1, 2):
        chunk = data_bytes[i:i+2]
        
        # Decodifica como inteiro Little Endian (B0B1)
        try:
            raw_value = int.from_bytes(chunk, byteorder='little', signed=False)
            
            # Converte para o valor real (decimal dividido por 100)
            temperature = raw_value / 100.0
            
            temperatures.append(f"{temperature:.2f}")
        except Exception as e:
            sys.stderr.write(f"❌ Erro de decodificação no chunk {i}-{i+1}: {e}\n")


    print("\n--- Resultados de Temperatura Decodificados (CSV) ---")
    print(f"Total de pontos de dados processados: {len(temperatures)}")
    print("\nTemperatura (Celsius):")
    # Imprime os valores separados por vírgula
    print(",".join(temperatures))
    print("=" * 90)


def main():
    """Configura e executa a lógica principal."""
    parser = argparse.ArgumentParser(
        description="Conecta, ativa, loga o stream de dados BLE e processa o resultado final."
    )
    parser.add_argument(
        'address',
        type=str,
        help="O endereço MAC (Bluetooth Address) do dispositivo alvo (ex: 'FE:98:00:30:39:44')."
    )
    
    args = parser.parse_args()
    asyncio.run(run_raw_logger(args.address))

if __name__ == "__main__":
    main()
