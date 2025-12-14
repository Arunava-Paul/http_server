//init
/*
 * HTTP client example
 * IPv4 only, no TLS
 * GET + PUT to /11
 */

#include <zephyr/logging/log.h>
LOG_MODULE_REGISTER(net_http_client_sample, LOG_LEVEL_DBG);

#include <zephyr/net/net_ip.h>
#include <zephyr/net/socket.h>
#include <zephyr/net/http/client.h>

#define SERVER_ADDR4 "192.168.0.103"
#define SERVER_PORT  8888
#define SERVER_PATH  "/11"

#define MAX_RECV_BUF_LEN 512

static uint8_t recv_buf[MAX_RECV_BUF_LEN];

/* -------------------------------------------------- */
/* Socket creation + connect                          */
/* -------------------------------------------------- */
static int connect_http_socket(int *sock, struct sockaddr_in *addr)
{
	memset(addr, 0, sizeof(*addr));

	addr->sin_family = AF_INET;
	addr->sin_port = htons(SERVER_PORT);

	if (inet_pton(AF_INET, SERVER_ADDR4, &addr->sin_addr) != 1) {
		LOG_ERR("Invalid server address");
		return -EINVAL;
	}

	*sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
	if (*sock < 0) {
		LOG_ERR("Socket create failed (%d)", -errno);
		return -errno;
	}

	if (connect(*sock, (struct sockaddr *)addr, sizeof(*addr)) < 0) {
		LOG_ERR("Connect failed (%d)", -errno);
		close(*sock);
		*sock = -1;
		return -errno;
	}

	return 0;
}

/* -------------------------------------------------- */
/* HTTP response callback                             */
/* -------------------------------------------------- */
static int response_cb(struct http_response *rsp,
		       enum http_final_call final_data,
		       void *user_data)
{
	if (final_data == HTTP_DATA_MORE) {
		LOG_INF("Partial data received (%zd bytes)", rsp->data_len);
	} else {
		LOG_INF("All data received (%zd bytes)", rsp->data_len);
	}

	LOG_INF("Response tag: %s", (const char *)user_data);
	LOG_INF("HTTP status: %s", rsp->http_status);

	return 0;
}

/* -------------------------------------------------- */
/* HTTP GET /11                                       */
/* -------------------------------------------------- */
static int http_get_request(void)
{
	struct sockaddr_in addr;
	struct http_request req = { 0 };
	int sock, ret;

	ret = connect_http_socket(&sock, &addr);
	if (ret < 0) {
		return ret;
	}

	req.method = HTTP_GET;
	req.url = SERVER_PATH;
	req.host = SERVER_ADDR4;
	req.protocol = "HTTP/1.1";
	req.response = response_cb;
	req.recv_buf = recv_buf;
	req.recv_buf_len = sizeof(recv_buf);

	ret = http_client_req(sock, &req,
			      3 * MSEC_PER_SEC,
			      "GET /11");

	close(sock);
	return ret;
}

/* -------------------------------------------------- */
/* HTTP PUT /11                                       */
/* -------------------------------------------------- */
static int http_put_request(void)
{
	struct sockaddr_in addr;
	struct http_request req = { 0 };
	int sock, ret;

	const char *payload = "foobar";

	ret = connect_http_socket(&sock, &addr);
	if (ret < 0) {
		return ret;
	}

	req.method = HTTP_PUT;
	req.url = SERVER_PATH;
	req.host = SERVER_ADDR4;
	req.protocol = "HTTP/1.1";
	req.payload = payload;
	req.payload_len = strlen(payload);
	req.response = response_cb;
	req.recv_buf = recv_buf;
	req.recv_buf_len = sizeof(recv_buf);

	ret = http_client_req(sock, &req,
			      3 * MSEC_PER_SEC,
			      "PUT /11");

	close(sock);
	return ret;
}

/* -------------------------------------------------- */
/* Main                                               */
/* -------------------------------------------------- */
int main(void)
{
	while (1) {
		if (http_get_request() < 0) {
			break;
		}

		if (http_put_request() < 0) {
			break;
		}

		k_sleep(K_SECONDS(5));
	}

	return 0;
}