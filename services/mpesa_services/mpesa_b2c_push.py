import os
import base64
import aiohttp
import logging
import uuid

from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509

from services.mpesa_services.mpesa_stk_push import MpesaTokenManager

load_dotenv()
logger = logging.getLogger(__name__)


class B2CPaymentService:
    def __init__(self):
        self.cert_path = os.getenv("SAFARICOM_CERT_PATH")
        self.initiator_name = os.getenv("SAFARICOM_INITIATOR_NAME")
        self.initiator_password = os.getenv("SAFARICOM_INITIATOR_PASSWORD")
        self.shortcode = os.getenv("MPESA_SHORT_CODE")
        self.timeout_url = os.getenv("B2C_TIMEOUT_URL")
        self.success_url = os.getenv("B2C_SUCCESS_URL")
        self.request_url = os.getenv("B2C_REQUEST_URL")

        self.token_manager = MpesaTokenManager()

    async def generate_security_credential(self):
        try:
            with open(self.cert_path, "rb") as cert_file:
                cert_data = cert_file.read()
                
            # Load the X.509 certificate and extract the public key
            try:
                # First try to load as X.509 certificate
                certificate = x509.load_pem_x509_certificate(cert_data)
                public_key = certificate.public_key()
                logger.info("Successfully loaded X.509 certificate and extracted public key")
                
            except ValueError:
                # If that fails, try to load as PEM public key directly
                try:
                    public_key = serialization.load_pem_public_key(cert_data)
                    logger.info("Successfully loaded PEM public key")
                except ValueError as e:
                    logger.error(f"Failed to load certificate in any format: {e}")
                    raise ValueError(f"Unable to load certificate: {e}")

            # Encrypt the password using RSA PKCS1v15 padding
            encrypted = public_key.encrypt(
                self.initiator_password.encode('utf-8'),
                padding.PKCS1v15()
            )

            # Encode to base64
            security_credential = base64.b64encode(encrypted).decode('utf-8')
            logger.info("Security credential generated successfully")
            return security_credential
            
        except Exception as e:
            logger.error(f'Security credential encryption failed: {e}')
            raise RuntimeError('Failed to generate security credential')

    async def build_payload(self, amount: int, recipient_phone: str):
        try:
            security_credential = await self.generate_security_credential()

            # we also need to generate a unique originatorconversationid for the api we do using the uuid for unique 128 bit values 
            originator_conversation_id = str(uuid.uuid4())
            
            payload = {
                "OriginatorConversationID": originator_conversation_id,
                "Initiator": self.initiator_name,
                "SecurityCredential": security_credential,
                "CommandID": "BusinessPayment",  # Changed from BusinessPayToBulk
                "SenderIdentifierType": "4",
                "RecieverIdentifierType": "1",
                "Amount": str(amount),
                "PartyA": str(self.shortcode),
                "PartyB": recipient_phone,
                "AccountReference": "customer_withdrawal",
                "Requester": recipient_phone,
                "Remarks": "account funds withdrawal",
                "QueueTimeOutURL": self.timeout_url,
                "ResultURL": self.success_url
            }
            
            logger.info(f"B2C payload built for amount: {amount}, phone: {recipient_phone}")
            return payload
            
        except Exception as e:
            logger.error(f'Failed to build B2C payload: {e}')
            raise RuntimeError('Failed to build B2C payload')

    async def send_b2c_request(self, amount: int, phone: str):
        try:
            # Get access token
            access_token = self.token_manager.get_token()
            if not access_token:
                raise RuntimeError("Failed to obtain access token")
            
            # Build payload
            payload = await self.build_payload(amount, phone)

            # Set headers
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            logger.info(f"Sending B2C request to: {self.request_url}")
            
            # Make the request
            async with aiohttp.ClientSession() as session:
                async with session.post(self.request_url, json=payload, headers=headers) as response:
                    response_data = await response.json()
                    
                    logger.info(f"B2C response status: {response.status}")
                    logger.info(f"B2C response data: {response_data}")
                    
                    if response.status == 200:
                        return response_data
                    else:
                        logger.error(f"B2C request failed with status {response.status}: {response_data}")
                        return response_data
                        
        except Exception as e:
            logger.error(f'Failed to send the B2C request: {e}')
            raise RuntimeError(f'The B2C request failed: {str(e)}')