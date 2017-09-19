.. _config_options:

Configuration options
=====================

datasets
--------

Example:

.. code-block:: yaml

  datasets:
    BRK:
      name: Kadaster data
      scopes:
        VKS:
          summary: view kadastraal subject
        VKO:
          summary: view kadastraal object


+-----------------------+------------+----------------------------------------+
| Option name           | Value Type | Description                            |
+=======================+============+========================================+
| [1-4 word characters] | object     | Dataset identifier.                    |
+-----------------------+------------+----------------------------------------+

authorization_service
---------------------

Example:

.. code-block:: yaml

  authorization_service:
    root_path: /oauth2
    bind_host: localhost
    bind_port: 8110
    idps:
      tma_oauth2:
        client_id: ${TMA_OAUTH2_CLIENT_ID}
        authorization_uri: ${TMA_OAUTH2_AUTHZ_URI}

+-----------------------+------------+----------------------------------------+
| Option name           | Value Type | Description                            |
+=======================+============+========================================+
| bind_host             | string     | Hostname of the interface the server   |
|                       |            | will bind on. (Required)               |
+-----------------------+------------+----------------------------------------+
| bind_port             | integer    | Port the server will bind on.          |
|                       |            | (Required)                             |
+-----------------------+------------+----------------------------------------+
| external_fqdn         | string     | Hostname that is used by clients       |
|                       |            | to contact the server. Used when       |
|                       |            | running behind a load balancer or      |
|                       |            | other proxy. (Optional, default )      |
+-----------------------+------------+----------------------------------------+
