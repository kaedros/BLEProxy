#include <stdio.h>
#include <string.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gattc_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_defs.h"
#include "esp_mac.h"

#define TAG "BLE_PROXY"

// Nome que o ESP vai anunciar para o app mobile
// #define LOCAL_DEVICE_NAME "ESP32_PROXY"
#define LOCAL_DEVICE_NAME "TIAGO-U105"

// MAC do dispositivo BLE alvo (substitua pelo real)
static esp_bd_addr_t target_bda = {0xFE, 0x98, 0x00, 0x30, 0x39, 0x45};

// UUID de serviço: 0x1809
static uint8_t service_uuid128[16] = {
	0xfb, 0x34, 0x9b, 0x5f, 0x80, 0x00, 0x00, 0x80, 0x00, 0x10, 0x00, 0x00,
	0x09, 0x18, // <-- 0x1809
	0x00, 0x00};

// UUID de 16 bits para Service Data
static uint16_t service_data_uuid = 0xC1C5;

// Payload capturado do dispositivo original
static uint8_t service_data_payload[] = {0xFE, 0x98, 0x00, 0x30, 0x39, 0x44, 0xE4, 0x0C, 0x7F, 0x08, 0x1D, 0x04, 0x00, 0x00, 0x04, 0x46, 0x60, 0x09, 0x00, 0x0A};

// Buffer final (UUID + payload)
static uint8_t service_data[2 + sizeof(service_data_payload)];

void prepare_service_data() {
	service_data[0] = service_data_uuid & 0xFF;
	service_data[1] = (service_data_uuid >> 8) & 0xFF;
	memcpy(&service_data[2], service_data_payload, sizeof(service_data_payload));
}

// Dados de advertising
esp_ble_adv_data_t adv_data = {
	.set_scan_rsp = false,
	.include_name = true,
	.include_txpower = false,
	.min_interval = 0x20,
	.max_interval = 0x40,
	.appearance = 0x00,
	.manufacturer_len = 0,
	.p_manufacturer_data = NULL,
	// .service_data_len = 0,
	// .p_service_data = NULL,
	// Service Data (UUID 128 + Payload)
	.service_data_len = sizeof(service_data),
	.p_service_data = service_data,
	.service_uuid_len = sizeof(service_uuid128),
	.p_service_uuid = service_uuid128,
	.flag = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
};

// Parâmetros de advertising
esp_ble_adv_params_t adv_params = {
	.adv_int_min = 0x20,
	.adv_int_max = 0x40,
	.adv_type = ADV_TYPE_IND,
	.own_addr_type = BLE_ADDR_TYPE_PUBLIC,
	.peer_addr = {0},
	.peer_addr_type = BLE_ADDR_TYPE_PUBLIC,
	.channel_map = ADV_CHNL_ALL,
	.adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

static esp_gatt_if_t gattc_if_global = 0;
static uint16_t gattc_conn_id_global = 0;
static bool connected = false;

// --- GAP callback (scanning, conexão, etc.)
static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param) {
	switch (event) {
	case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
		ESP_LOGI(TAG, "Advertising data set complete, starting advertising...");
		prepare_service_data();
		esp_ble_gap_start_advertising(&adv_params); // depois de configurado, inicie advertising
		break;

	case ESP_GAP_BLE_ADV_START_COMPLETE_EVT:
		ESP_LOGI("GAP", "Advertising started");
		break;
	case ESP_GAP_BLE_SCAN_RESULT_EVT:
		ESP_LOGI(TAG, "Scan result...");
		break;
	default:
		break;
	}
}

// --- GATTC callback (cliente que conecta no dispositivo alvo)
static void gattc_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if, esp_ble_gattc_cb_param_t *param) {
	switch (event) {
	case ESP_GATTC_REG_EVT: {
		ESP_LOGI(TAG, "GATTC Registered, starting connect... conectando ao MOT-U105");
		gattc_if_global = gattc_if;
		esp_ble_gattc_open(gattc_if_global, target_bda, BLE_ADDR_TYPE_PUBLIC, true);
		break;
	}

	case ESP_GATTC_OPEN_EVT: {
		if (param->open.status == ESP_GATT_OK) {
			ESP_LOGI(TAG, "GATTC connected to MOT-U105");
			gattc_conn_id_global = param->open.conn_id;
			connected = true;
			// iniciar busca de serviços
			esp_ble_gattc_search_service(gattc_if, param->open.conn_id, NULL);
		}
		else {
			ESP_LOGE(TAG, "Failed to open GATTC MOT-U105 conn, status 0x%x", param->open.status);
		}
		break;
	}

	case ESP_GATTC_SEARCH_RES_EVT: {
		// esp_gatt_srvc_id_t srvc_id = param->search_res.srvc_id;
		esp_gatt_srvc_id_t srvc_id;
		memcpy(&srvc_id, &param->search_res.srvc_id, sizeof(esp_gatt_srvc_id_t));

		if (srvc_id.id.uuid.len == ESP_UUID_LEN_16) {
			ESP_LOGI(TAG, "Service found UUID16: 0x%04x", srvc_id.id.uuid.uuid.uuid16);
		}
		break;
	}

	case ESP_GATTC_SEARCH_CMPL_EVT: {
		ESP_LOGI(TAG, "Service search complete, now listing characteristics...");

		uint16_t count = 0;
		esp_ble_gattc_get_attr_count(gattc_if,
									 gattc_conn_id_global,
									 ESP_GATT_DB_CHARACTERISTIC,
									 0, 0, 0, &count);
		if (count > 0) {
			esp_gattc_char_elem_t *char_elem_result =
				malloc(sizeof(esp_gattc_char_elem_t) * count);
			if (char_elem_result) {
				esp_ble_gattc_get_all_char(gattc_if,
										   gattc_conn_id_global,
										   0, 0,
										   char_elem_result,
										   &count, 0);
				for (int i = 0; i < count; i++) {
					ESP_LOGI(TAG, "Char UUID: 0x%04x handle %d",
							 char_elem_result[i].uuid.uuid.uuid16,
							 char_elem_result[i].char_handle);
				}
				free(char_elem_result);
			}
		}
		break;
	}

	case ESP_GATTC_NOTIFY_EVT:
		ESP_LOGI(TAG, "Notify received, len=%d", param->notify.value_len);
		ESP_LOG_BUFFER_HEX(TAG, param->notify.value, param->notify.value_len);
		break;

	default:
		break;
	}
}

// --- GATTS callback (servidor para o app mobile conectar)
static void gatts_event_handler(esp_gatts_cb_event_t event, esp_gatt_if_t gatts_if, esp_ble_gatts_cb_param_t *param) {
	switch (event) {
	case ESP_GATTS_REG_EVT:
		ESP_LOGI(TAG, "GATTS Registered, starting advertising...");

		// define o nome
		esp_ble_gap_set_device_name(LOCAL_DEVICE_NAME);

		// define os dados de advertising
		prepare_service_data();
		esp_err_t ret = esp_ble_gap_config_adv_data(&adv_data);
		if (ret) {
			ESP_LOGE(TAG, "esp_ble_gap_config_adv_data failed: %s", esp_err_to_name(ret));
		}
		break;

	case ESP_GATTS_CONNECT_EVT:
		ESP_LOGI(TAG, "GATTS App Mobile connected as client");
		// ESP_LOGI(TAG, "App connected, conn_id=%d", param->connect.conn_id);
		// gatts_conn_id = param->connect.conn_id;
		// // se ainda não conectado ao target, tente abrir
		// if (!target_connected && gattc_if_global != 0xff) {
		// 	ESP_LOGI(TAG, "Attempting preconnect to target because an App connected");
		// 	esp_ble_gattc_open(gattc_if_global, (uint8_t *)TARGET_BDA, TARGET_ADDR_TYPE, true);
		// }
		break;

	case ESP_GATTS_DISCONNECT_EVT:
		ESP_LOGI(TAG, "GATTS App Mobile disconnected");
		break;

	default:
		break;
	}
}

void app_main(void) {
	ESP_LOGI(TAG, "Starting BLE Proxy...");

	esp_err_t ret = nvs_flash_init();
	if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
		ESP_ERROR_CHECK(nvs_flash_erase());
		ESP_ERROR_CHECK(nvs_flash_init());
	}

	ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));
	esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
	/* Novo MAC desejado (exemplo) */
	uint8_t new_mac[6] = {0xFE, 0x98, 0x00, 0x30, 0x39, 0x45}; // mesmo do MOT-U105

	/* Define o endereço BLE */
	ret = esp_base_mac_addr_set(new_mac);
	if (ret != ESP_OK) {
		ESP_LOGE(TAG, "Falha ao setar MAC base: %s", esp_err_to_name(ret));
	}
	ret = esp_read_mac(new_mac, ESP_MAC_BT);
	if (ret == ESP_OK) {
		ESP_LOGI(TAG, "Novo MAC BLE configurado: %02X:%02X:%02X:%02X:%02X:%02X",
				 new_mac[0], new_mac[1], new_mac[2], new_mac[3], new_mac[4], new_mac[5]);
	}
	ESP_ERROR_CHECK(esp_bt_controller_init(&bt_cfg));
	ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_BLE));

	ESP_ERROR_CHECK(esp_bluedroid_init());
	ESP_ERROR_CHECK(esp_bluedroid_enable());

	// Registra callbacks
	ESP_ERROR_CHECK(esp_ble_gap_register_callback(gap_event_handler));
	ESP_ERROR_CHECK(esp_ble_gattc_register_callback(gattc_event_handler));
	ESP_ERROR_CHECK(esp_ble_gatts_register_callback(gatts_event_handler));

	// Registra apps GATT cliente/servidor
	ESP_ERROR_CHECK(esp_ble_gattc_app_register(0));
	ESP_ERROR_CHECK(esp_ble_gatts_app_register(0));
}
