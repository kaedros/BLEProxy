#
# Escanear e exibir detalhes de dispositivos Bluetooth Low Energy (BLE)
# nas proximidades usando a biblioteca Bleak.
#
# Funcionalidades:
# 1. Exibe *todos* os dispositivos encontrados, atribuindo "Sem Nome" aos anonimos.
# 2. Permite filtrar apenas dispositivos que possuem um nome (opcao -n).
# 3. Permite filtrar dispositivos que contem uma sequencia de texto especifica no nome (opcao -f).
#
import asyncio
import argparse
from bleak import BleakScanner

# Conjunto global para rastrear enderecos de dispositivos ja exibidos para evitar duplicatas
seen_devices = set()

# Variaveis globais para armazenar os filtros (serao definidas por argparse)
NAME_FILTER = None
ONLY_NAMED = False

def detection_callback(device, advertisement_data):
    """Callback chamado para cada pacote de anuncio BLE recebido."""
    global NAME_FILTER
    global ONLY_NAMED

    address = device.address
    rssi = advertisement_data.rssi
    
    name = device.name or "Sem Nome"
    has_name = device.name is not None and device.name.strip() != "" # Verifica se o nome existe e nao e vazio/espacos

    if ONLY_NAMED and not has_name:
        return # Ignora se o usuario pediu apenas nomeados e este nao tem

    if NAME_FILTER and has_name:
        if NAME_FILTER.lower() not in name.lower():
            return  # Ignora se o nome nao contem a sequencia do filtro

    if address in seen_devices:
        return  # Ignora se o endereco ja foi mostrado

    seen_devices.add(address) # Marca o endereco como visto

    # === Exibe informacoes do dispositivo ===
    print(f"🔍 Dispositivo encontrado:")
    print(f"  Nome: {name}")
    print(f"  Endereco: {address}")
    print(f"  RSSI: {rssi} dBm")

    # Dados de Anuncio Adicionais
    
    # Flags (pode nao estar disponivel no Windows)
    flags = getattr(advertisement_data, "flags", None)
    if flags is not None:
        print(f"  Flags: 0x{flags:02X}")
    else:
        print("  Flags: N/A")

    # Potencia de Transmissao (TX Power)
    tx_power = getattr(advertisement_data, "tx_power", None)
    if tx_power is not None:
        print(f"  Potencia de Transmissao (TX Power): {tx_power} dBm")
    else:
        print("  Potencia de Transmissao (TX Power): N/A")

    # UUIDs de Servico
    service_uuids = getattr(advertisement_data, "service_uuids", None) or []
    if service_uuids:
        uuid_list = ", ".join([f"`{uuid}`" for uuid in service_uuids])
        print(f"  Servicos BLE: [{uuid_list}]")
    else:
        print("  Servicos BLE: Nenhum")

    # Dados do Fabricante
    manufacturer_data = getattr(advertisement_data, "manufacturer_data", None) or {}
    if manufacturer_data:
        print("  Dados do Fabricante:")
        for company_id, data in manufacturer_data.items():
            hex_data = data.hex().upper()
            print(f"    ID Empresa 0x{company_id:04X}: {hex_data}")
    else:
        print("  Dados do Fabricante: Nenhum")

    # Dados de Servico
    service_data = getattr(advertisement_data, "service_data", None) or {}
    if service_data:
        print("  Dados de Servico:")
        for uuid, data in service_data.items():
            hex_data = data.hex().upper()
            print(f"    {uuid}: {hex_data}")
    else:
        print("  Dados de Servico: Nenhum")

    print("-" * 60)

async def main():
    """Funcao principal assincrona que configura e inicia o escaneamento."""
    global seen_devices
    global NAME_FILTER
    global ONLY_NAMED

    # 1. Configura a analise de argumentos
    parser = argparse.ArgumentParser(
        description="Escaneia dispositivos BLE e oferece opcoes de filtragem.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-t', '--timeout',
        type=float,
        default=10.0,
        help="Duracao do escaneamento em segundos (padrao: 10.0)."
    )
    parser.add_argument(
        '-f', '--filter',
        type=str,
        default=None,
        help="Texto para filtrar o nome do dispositivo.\nApenas dispositivos cujo nome *contem* este texto serao exibidos.\n(A filtragem e Case-Insensitive e so funciona se o dispositivo tiver um nome)."
    )
    parser.add_argument(
        '-n', '--only-named',
        action='store_true',
        help="Se presente, o script exibira APENAS dispositivos que possuem um nome de anuncio (ignora os 'Sem Nome')."
    )
    
    args = parser.parse_args()

    # 2. Define as variaveis globais do filtro
    NAME_FILTER = args.filter
    ONLY_NAMED = args.only_named

    # Reinicia o conjunto de dispositivos vistos ao comecar
    seen_devices = set() 

    # Mensagem informativa
    filter_info = []
    if ONLY_NAMED:
        filter_info.append("APENAS DISPOSITIVOS NOMEADOS")
    else:
        filter_info.append("TODOS (incluindo 'Sem Nome')")

    if NAME_FILTER:
        filter_info.append(f"FILTRANDO NOME por: '{NAME_FILTER}'")

    print(f"📡 Iniciando escaneamento BLE ({args.timeout:.1f} segundos)...")
    print(f"   Modo de exibicao: {' | '.join(filter_info)}\n")

    try:
        # 3. Inicia o escaneamento
        await BleakScanner.discover(
            timeout=args.timeout,
            detection_callback=detection_callback
        )
        print(f"\n✅ Escaneamento concluido. {len(seen_devices)} dispositivo(s) unico(s) encontrado(s) e exibido(s).")

    except Exception as e:
        print(f"\n❌ Erro durante o escaneamento: {type(e).__name__}: {e}")
        # Dica para usuarios do Linux/macOS
        if 'permission' in str(e).lower():
             print("\n👉 Dica: Em sistemas Linux/macOS, a permissao pode ser um problema.")
             print("   - Linux: Tente usar 'sudo python seu_script.py'.")
             print("   - Certifique-se de que o Bluetooth esta ligado.")

if __name__ == "__main__":
    asyncio.run(main())