from flask import Flask, jsonify
import undetected_chromedriver as uc

app = Flask(__name__)

@app.route('/wd/hub/session', methods=['POST'])
def new_session():
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument("--disable-infobars")

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(300)

    executor_url = "http://100.122.137.82:4444"
    session_id = driver.session_id

    return jsonify({"sessionId": session_id, "executor_url": executor_url})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=4444)
