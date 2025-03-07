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

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(300)

    response_data = {
        "sessionId": driver.session_id,
        "executor_url": driver.command_executor._url
    }

    return jsonify(response_data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=4444)
