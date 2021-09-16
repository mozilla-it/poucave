from telescope import config


def options_from_params(root_url, client_id, access_token, certificate):
    return {
        "rootUrl": root_url,
        "credentials": (
            {"clientId": client_id.rstrip(), "accessToken": access_token.rstrip()}
            if client_id and access_token
            else {"certificate": certificate}
        ),
        "maxRetries": config.REQUESTS_MAX_RETRIES,
    }
