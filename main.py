import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from flask import Flask, request, jsonify
import threading

from selenium.webdriver.common.action_chains import ActionChains


app = Flask(__name__)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
    return response


@app.route('/book', methods=['POST', 'OPTIONS'])
def book():
    # 处理预检请求
    if request.method == 'OPTIONS':
        return '', 200

    # 处理实际POST请求
    data = request.json
    thread = threading.Thread(target=auto_booking_func, args=(data,))
    thread.daemon = True
    thread.start()
    return jsonify({'status': '任务已启动'})


def auto_booking_func(data):
    usernameVBS = data['username']
    passwordVBS = data['password']
    fresh_frequency = data['frequency']

    containers = []
    for containerInfos in data['bookings']:
        containerinfo = {'containerId': containerInfos['containerId'], 'date': containerInfos['date'], 'type': containerInfos['type']}
        containers.append(containerinfo)

    add_containers = containers.copy()
    driver = webdriver.Chrome()

    driver.get("https://www.1-stop.biz")

    launch_btn = driver.find_element(By.XPATH, "//a[@href='https://www.1-stop.biz/launch']")
    launch_btn.click()

    vehicle_booking_system_btn = driver.find_element(By.XPATH, "//a[@href='https://vbs.1-stop.biz/SignIn.aspx']")
    vehicle_booking_system_btn.click()

    handles = driver.window_handles
    driver.switch_to.window(handles[-1])

    username_inputBox = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    username_inputBox.send_keys(usernameVBS)

    password_inputBox = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "password"))
    )
    password_inputBox.send_keys(passwordVBS)

    action_btn = driver.find_element(
        By.XPATH,
        "//button[text()='Continue' and not(contains(@class, 'ulp-hidden-form-submit-button'))]"
    )
    action_btn.click()

    select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "vbs_new_selected_facilityid"))
    )
    select = Select(select_element)
    select.select_by_visible_text("DP WORLD Port Botany")

    accept_btn = driver.find_element(By.ID, "Accept")
    accept_btn.click()

    container_list_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.LINK_TEXT, "Container List"))
    )
    container_list_btn.click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#CBItemsGrid"))
    )

    container_links = driver.find_elements(
        By.CSS_SELECTOR,
        "#CBItemsGrid tbody tr td div div.link_box"
    )

    containers_in_page = [link.text.strip() for link in container_links if link.text.strip()]

    for containerInfo in containers:
        if containerInfo['containerId'] in containers_in_page:
            add_containers.remove(containerInfo)

    # 此处添加container过程先忽略

    for add_container in add_containers:

        add_containers_btn = driver.find_element(By.ID, "show_add_containers")
        add_containers_btn.click()

        value_select = "IMPORT" if add_container['type'] == 0 else "EXPORT"
        # # 通过 value 选择

        driver.execute_script("""
            var select = document.getElementById('DIRECTION');

            // 强制修改 display 属性
            select.style.display = 'block';
            select.style.visibility = 'visible';
            select.style.opacity = '1';

            // 也可以移除可能的内联样式
            select.style.removeProperty('display');
            select.style.removeProperty('visibility');
            select.style.removeProperty('opacity');

            // 如果有隐藏类，移除它
            select.classList.remove('hidden', 'hide', 'invisible');

            console.log('select 已强制显示');
        """)

        time.sleep(1)

        select_btn = driver.find_element(By.NAME, 'CBIUploadConatinersForm___DIRECTION')
        select_btn.click()

        select = Select(driver.find_element(By.NAME, 'CBIUploadConatinersForm___DIRECTION'))
        select.select_by_value(value_select)

        # 验证方法1：获取当前选中的 option
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "CBIUploadConatinersForm___CONTAINERS"))
        )
        textarea.send_keys(add_container['containerId'])

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "cbi_add_containers_btn"))
        ).click()

        driver.find_element(By.CLASS_NAME, "blockUI-close").click()

        time.sleep(1)
    #

    time.sleep(5)
    for add_container in containers:
        try:
            containerId = add_container['containerId']
            # 行ID格式: CBIRowId_DRYU9575014_IMPORT
            # 可以使用部分匹配
            row_id_prefix = f"CBIRowId_{containerId}"

            # 找到包含目标Container的行
            row = driver.find_element(By.CSS_SELECTOR, f"tr[id^='{row_id_prefix}']")

            # 在该行内找到Book列的checkbox（第20列）
            checkbox = row.find_element(By.CSS_SELECTOR, "td:nth-child(20) input[type='checkbox']")

            # 如果未选中，则勾选
            if not checkbox.is_selected():
                checkbox.click()
                print(f"✅ 已勾选Container: {containerId}")
            else:
                print(f"ℹ️ Container: {containerId} 已经是选中状态")

        except Exception as e:
            print(f"❌ 未找到Container: {containerId}, 错误: {e}")

    start_book_btn = driver.find_element(By.ID, 'start_booking')
    start_book_btn.click()

    for book_container in containers:
        select_container_element_id = "BCSCntrRow_" + book_container["containerId"] + "_IMPORT"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, select_container_element_id))
        ).click()

        select_container_element_date = book_container["date"].split(":")[0]
        select_container_element_time = book_container["date"].split(":")[1]
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,  # ⚠️ 注意这里是双括号
                                                f"//div[@class='calendarbar-item calendarbar-day' and text()='{select_container_element_date}']"))
            ).click()
        except:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,  # ⚠️ 双括号
                                                f"//div[contains(@class, 'calendarbar-day') and contains(text(), '{select_container_element_date}')]"))
            ).click()

            # 2. 重试直到zone可用
        selected = False
        i = 0
        while not selected:
            # 检查zone是否可用
            i = i + 1
            try:
                zone_row = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, f"tr_zone_{select_container_element_time}"))
                )

                pick_up_cell = WebDriverWait(zone_row, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "td.slots_cell:nth-child(2)"))
                )

                type_class = "pick_up_bg" if book_container["type"] == 0 else "drop_off_bg"
                if pick_up_cell.find_elements(By.CLASS_NAME, type_class):
                    select_button = WebDriverWait(zone_row, 10).until(
                        EC.presence_of_element_located((By.XPATH, ".//div[@class='link_box' and text()='Select']"))
                    )
                    driver.execute_script("arguments[0].click();", select_button)
                    print(f"✅ Zone {select_container_element_time} 选择成功")
                    time.sleep(1)
                    selected = True
                    break
                else:
                    print(f"刷新第{i}次，Zone {select_container_element_time}不可用，每{fresh_frequency}秒刷新一次")
                    time.sleep(fresh_frequency)
                    refresh = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "SlotsRefresh"))
                    )
                    refresh.click()
                    continue

            except Exception as e:
                driver.find_element(By.ID, "SlotsRefresh").click()
                print(f"刷新第{i + 1}次，发生异常: " + e)

    driver.find_element(By.ID, "Confirm").click()

    # driver.quit()


if __name__ == "__main__":
    print("Flask服务启动在 http://127.0.0.1:5000")
    app.run(debug=True, port=5000)