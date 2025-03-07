from flask import Flask, jsonify
import undetected_chromedriver as uc

app = Flask(__name__)

REMOTE_SERVER = "http://100.122.137.82:4444"

@app.route('/wd/hub/session', methods=['POST'])
def create_session():
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(300)

    executor_url = f"{REMOTE_SERVER}/wd/hub"
    session_id = driver.session_id

    return jsonify({"value": {"sessionId": session_id, "executor_url": executor_url}})
