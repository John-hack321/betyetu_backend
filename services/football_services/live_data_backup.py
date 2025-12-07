import logging
import os
from dotenv import load_dotenv

load_dotenv()


logger= logging.getLogger(__name__)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
class LiveDataServiceBackup():
    def __init__(self):
        self.football_data_api_key = os.getenv('FOOTBALL_API_KEY')
        self.livefootball_data_api_url = os.getenv('LIVE_FOOTBALL_API_URL')

    async def get_todays_matches_from_db():
        pass









liveDataBackup= LiveDataServiceBackup()