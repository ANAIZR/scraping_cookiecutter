from flask import Flask, jsonify
import undetected_chromedriver as uc

app = Flask(__name__)

@app.route('/wd/hub/session', methods=['POST'])
def create_session():
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(300)

    executor_url = "http://100.122.137.82:4444"  
    session_id = driver.session_id

    response = {
        "value": {
            "sessionId": session_id,
            "capabilities": {
                "browserName": "chrome",
                "browserVersion": driver.capabilities.get('browserVersion', ''),
                "platformName": driver.capabilities.get('platformName', ''),
                "goog:chromeOptions": {}
            }
        }
    }

    return jsonify(response)
