# BLE Proxy & Sniffer for IoT Devices

Intercepte, registre e redirecione a comunicação BLE entre dispositivos como o MOT-U105 e seus apps móveis

## Objetivo
Muitos dispositivos IoT usam Apps proprietários que limitam o acesso aos dados. Este projeto permite:
- 📥 Log contínuo dos dados (sem depender do app)
- 🔄 Integração com sistemas próprios (Home Assistant, nuvem, banco de dados)
- 🔍 Análise de protocolos BLE (engenharia reversa)
- 💡 Automação sem app — mesmo quando o app não está aberto

### O ESP32:
- Atua como BLE Peripheral → fingindo ser o dispositivo
- Conecta-se como BLE Central → ao verdadeiro dispositivo
- Encaminha todos os comandos e respostas
- Pode processar, armazenar ou enviar dados

### 🛠️ Tecnologias
- ESP32 (qualquer modelo com Bluetooth 4.2+)
- ESP-IDF v5.5.1 (NimBLE stack)
- Dual Role BLE: Central + Peripheral
- Código em C nativo (alta performance, baixo overhead)

### 📦 Pré-requisitos
- ESP-IDF v5.5.1 instalado (guia oficial )
- ESP32 com pelo menos 4MB de flash (recomendado)
- Python + bleak (opcional, para testes no PC)
- Dispositivo BLE alvo

## Como usar

1. Clone o repositório
```bash
git clone https://github.com/kaedros/BLEProxy.git
cd bleproxy
```

2. Compile, envie e monitore
```bash
idf.py flash monitor
```

## Funcionalidades principais
| Função | Descrição |
|-------|----------|
| Spoofing de dispositivo | Finge ser o dispositivo (nome, UUIDs) |
| Encaminhamento transparente | App pensa que está conectado diretamente |
| Logging em tempo real | Dados capturados via serial ou armazenados |
| Compatível com múltiplos dispositivos | Basta ajustar UUIDs e MAC |
| Extensível | Adicione WiFi, MQTT, OTA, etc. |