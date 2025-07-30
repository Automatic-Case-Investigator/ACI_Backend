# ACI Backend

This is the main local backend designed to interface with the AI server and integrate with SIEM and SOAR platforms to coordinate investigations.

## Supported Platforms

### SOAR
- [The Hive](https://strangebee.com/)

### SIEM
- [Wazuh](https://wazuh.com/)

## Installation

### Using Docker

1. Copy the sample environment file and customize it to your setup:
   ```bash
   cp sample.env .env
   ```


2. Build and run the docker compose project:
  
    **Linux / Mac:**
    ```bash
    sudo docker compose -f docker-compose.yml build
    sudo docker compose -f docker-compose.yml up
    ```
    
    **Windows:**
    ```bash
    sudo docker compose -f docker-compose-windows.yml build
    sudo docker compose -f docker-compose-windows.yml up
    ```
