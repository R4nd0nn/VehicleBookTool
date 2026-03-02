import time
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from flask import Flask, request, jsonify, render_template
import threading
import logging
import datetime

app = Flask(__name__)


# 获取打包后的资源路径
def get_resource_path(relative_path):
    """获取打包后的资源文件路径"""
    try:
        # PyInstaller创建临时文件夹_MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# 设置模板文件夹路径
template_dir = get_resource_path('templates')
app.template_folder = template_dir


def get_log_path():
    """获取日志文件路径，确保输出到exe同级目录"""
    if getattr(sys, 'frozen', False):
        # 打包成exe运行时：获取exe所在目录
        exe_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境运行时：当前目录
        exe_dir = os.path.abspath(".")

    # 确保目录存在
    if not os.path.exists(exe_dir):
        os.makedirs(exe_dir)

    return os.path.join(exe_dir, 'booking_automation.log')


# 使用新的日志路径
log_file_path = get_log_path()

# 配置logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)


# ==================== Flask Routes ====================
@app.route('/')
def index():
    """Serve the frontend HTML page"""
    return render_template('booking_page.html')


@app.after_request
def after_request(response):
    """Add CORS headers"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
    return response


@app.route('/book', methods=['POST', 'OPTIONS'])
def book():
    """Handle booking request"""
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    thread = threading.Thread(target=auto_booking_func, args=(data,))
    thread.daemon = True
    thread.start()
    return jsonify({'status': 'Task started'})


# ==================== Selenium Automation Functions ====================
def login_vbs(driver, username, password):
    """Login to VBS system"""
    logging.info("Starting VBS login")

    driver.get("https://www.1-stop.biz")

    # Click Launch button
    launch_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='https://www.1-stop.biz/launch']"))
    )
    launch_btn.click()

    # Click Vehicle Booking System
    vbs_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='https://vbs.1-stop.biz/SignIn.aspx']"))
    )
    vbs_btn.click()

    # Switch to new window
    driver.switch_to.window(driver.window_handles[-1])

    # Enter username and password
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    username_input.send_keys(username)

    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "password"))
    )
    password_input.send_keys(password)

    # Click Continue
    continue_btn = driver.find_element(
        By.XPATH,
        "//button[text()='Continue' and not(contains(@class, 'ulp-hidden-form-submit-button'))]"
    )
    continue_btn.click()

    logging.info("Login successful")


def select_facility(driver, facility_name):
    """Select facility"""
    logging.info(f"Selecting facility: {facility_name}")

    select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "vbs_new_selected_facilityid"))
    )
    select = Select(select_element)

    facility_map = {
        "dpw": "DP WORLD Port Botany",
        "patrick": "Patrick Port Botany"
    }

    facility = facility_map.get(facility_name)  # 默认值
    select.select_by_visible_text(facility)

    # Click Accept
    accept_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "Accept"))
    )
    accept_btn.click()


def go_to_container_list(driver):
    """Navigate to Container List page"""
    logging.info("Navigating to Container List page")

    container_list_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Container List"))
    )
    container_list_btn.click()

    # Wait for table to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#CBItemsGridHolder"))
    )


def get_existing_containers(driver):
    """Get list of existing containers on the page"""
    container_links = driver.find_elements(
        By.CSS_SELECTOR,
        "#CBItemsGrid tbody tr td div div.link_box"
    )
    return [link.text.strip() for link in container_links if link.text.strip()]


def add_container_to_system(driver, container_info):
    """Add a single container to the system"""
    logging.info(f"Adding container: {container_info['containerId']}")

    # Click add button
    add_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "show_add_containers"))
    )
    add_btn.click()

    # Handle select selection
    value_select = "IMPORT" if container_info['type'] == 0 else "EXPORT"

    # Force display select
    driver.execute_script("""
        var select = document.getElementById('DIRECTION');
        select.style.display = 'block';
        select.style.visibility = 'visible';
        select.style.opacity = '1';
        select.classList.remove('hidden', 'hide', 'invisible');
    """)
    time.sleep(1)

    # Select type
    select = Select(driver.find_element(By.NAME, 'CBIUploadConatinersForm___DIRECTION'))
    select.select_by_value(value_select)

    # Enter Container ID
    textarea = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "CBIUploadConatinersForm___CONTAINERS"))
    )
    textarea.send_keys(container_info['containerId'])

    # Click add
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "cbi_add_containers_btn"))
    ).click()

    # Close popup
    time.sleep(1)
    driver.find_element(By.CLASS_NAME, "blockUI-close").click()

    logging.info(f"Container {container_info['containerId']} added successfully")


def select_containers_for_booking(driver, containers):
    """Select containers for booking"""
    logging.info("Starting container selection")

    for container in containers:
        try:
            container_id = container['containerId']
            row_id_prefix = f"CBIRowId_{container_id}"

            row = driver.find_element(By.CSS_SELECTOR, f"tr[id^='{row_id_prefix}']")
            checkbox = row.find_element(By.CSS_SELECTOR, "td:nth-child(20) input[type='checkbox']")

            if not checkbox.is_selected():
                checkbox.click()
                logging.info(f"Container selected: {container_id}")
            else:
                logging.info(f"Container: {container_id} already selected")

        except Exception as e:
            logging.error(f"Container not found: {container.get('containerId')}, error: {e}")


def book_single_container(driver, container, fresh_frequency, start_time):
    """Book a single container slot"""
    container_id = container['containerId']
    logging.info(f"Starting booking for container: {container_id}")

    # Select container row
    row_id = f"BCSCntrRow_{container_id}_IMPORT"
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, row_id))
    ).click()

    # Parse date and time
    date_parts = container['date'].split(":")
    select_date = date_parts[0]
    select_time = date_parts[1].lstrip('0')

    # Select date
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH, f"//div[@class='calendarbar-item calendarbar-day' and text()='{select_date}']"
            ))
        ).click()
    except:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH, f"//div[contains(@class, 'calendarbar-day') and contains(text(), '{select_date}')]"
            ))
        ).click()

    # Select zone
    return select_zone_with_retry(driver, select_time, container['type'], fresh_frequency, start_time, container_id)


def select_zone_with_retry(driver, zone_time, container_type, fresh_frequency, start_time, container_id):
    """Select zone with retry mechanism"""
    selected = False
    retry_count = 0

    book_time_gap_second = (start_time - datetime.datetime.now()).total_seconds()

    if book_time_gap_second > 0:
        time.sleep(book_time_gap_second)

    while not selected:
        retry_count += 1
        try:
            zone_row = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, f"tr_zone_{zone_time}"))
            )

            pick_up_cell = WebDriverWait(zone_row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "td.slots_cell:nth-child(2)"))
            )

            type_class = "pick_up_bg" if container_type == 0 else "drop_off_bg"

            if pick_up_cell.find_elements(By.CLASS_NAME, type_class):
                select_button = WebDriverWait(zone_row, 10).until(
                    EC.presence_of_element_located((By.XPATH, ".//div[@class='link_box' and text()='Select']"))
                )
                driver.execute_script("arguments[0].click();", select_button)
                logging.info(f"当前时间:{datetime.datetime.now()}, container：{container_id} 尝试预定{zone_time}点, 预定成功")
                selected = True
            else:
                logging.info(f"当前时间:{datetime.datetime.now()}, container：{container_id} 尝试预定{zone_time}点, 但当前没有余量，准备第{retry_count}次重试")
                refresh = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "SlotsRefresh"))
                )
                refresh.click()
                time.sleep(fresh_frequency)

        except Exception as e:
            logging.error(f"Retry {retry_count}, exception occurred: {str(e)}")
            try:
                driver.find_element(By.ID, "SlotsRefresh").click()
            except:
                pass
            time.sleep(fresh_frequency)

    if not selected:
        logging.error(f"Zone {zone_time} selection failed, exceeded max retries")

    return selected


def auto_booking_func(data):
    """Main automation function"""
    logging.info("Starting automated booking task")

    # Parse data
    username = data['username']
    password = data['password']
    fresh_frequency = float(data.get('frequency', 1))
    containers = data['bookings']
    facility = data['facility']
    start_time = datetime.datetime.fromisoformat(data['startTime'])

    driver = None
    try:
        driver = webdriver.Chrome()

        # Login process
        login_vbs(driver, username, password)
        select_facility(driver,facility)

        if facility == "dpw":
            go_to_container_list(driver)

            # Get existing containers
            existing_containers = get_existing_containers(driver)

            # Add non-existing containers
            containers_to_add = [c for c in containers if c['containerId'] not in existing_containers]

            for container in containers_to_add:
                add_container_to_system(driver, container)
                time.sleep(1)

            time.sleep(3)

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "Refresh"))
            ).click()

            time.sleep(3)

            # Select containers for booking
            select_containers_for_booking(driver, containers)

            # Click start booking
            start_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "start_booking"))
            )
            start_btn.click()

            # Book each container
            for container in containers:
                success = book_single_container(driver, container, fresh_frequency, start_time)
                if not success:
                    logging.warning(f"Container {container['containerId']} booking failed")

            #此处注释可以不走到最终确认
            # Click Confirm
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "Confirm"))
            ).click()
        elif facility == "patrick":
            # accept_btn = WebDriverWait(driver, 10).until(
            #     EC.element_to_be_clickable((By.ID, "Accept"))
            # )
            # accept_btn.click()

            time.sleep(5)

            book_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@href='SearchBookSlots.aspx?mnitm=154142190']"))
            )
            book_btn.click()

            type = "IMPORT" if containers['type'] == 0 else "EXPORT"

            select_type = Select(driver.find_element(By.ID, "BOOKINGTYPE"))

            # 通过 value 属性选中
            select_type.select_by_value(type)

            time.sleep(3)

            select_date = Select(driver.find_element(By.ID, "BOOKINGDATE"))
            select_date_time_group = containers['date'].split(":")[0].split("/")
            select_date_input = select_date_time_group[2] + "-" + select_date_time_group[1] + "-" + select_date_time_group[0]
            select_date.select_by_value(select_date_input)

            # Patrick的界面只能停留3分钟，所以在界面前开始等
            book_time_gap_second = (start_time - datetime.datetime.now()).total_seconds()

            if book_time_gap_second > 0:
                time.sleep(book_time_gap_second)

            search_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "Search"))
            )
            search_btn.click()

            # Switch to new window
            driver.switch_to.window(driver.window_handles[-1])

            order_times = []
            for slot in containers['slots']:
                order_times.append({
                    "time":slot['time'],
                    "count": slot['count']})

            task_done = False
            while not task_done:
                for order_time in order_times[:]:  # 关键：使用 [:] 创建副本
                    # 然后获取第二个td（可用票数）
                    slots_xpath = f"//td[text()='{order_time['time']}' and not(@class)]/following-sibling::td[1]"
                    slots_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, slots_xpath))
                    )
                    slots_text = slots_element.text.strip()

                    try:
                        slots_int = int(slots_text)
                    except ValueError:
                        print(f"时段 {order_time['time']} 的可用票数格式错误: {slots_text}")
                        continue

                    if slots_int > 0:
                        select_id = f"DDL_{select_date_input}_{order_time['time']}"

                        try:
                            timezone_select = Select(driver.find_element(By.ID, select_id))
                        except:
                            print(f"找不到select: {select_id}")
                            continue

                        need_count = int(order_time['count'])

                        if slots_int >= need_count:
                            # 可以满足全部需求
                            timezone_select.select_by_value(str(need_count))

                            timezone_book_btn = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.ID, f"btnBook_{select_date_input}_{order_time['time']}"))
                            )
                            timezone_book_btn.click()

                            continue_book_btn = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.ID, "Continue"))
                            )
                            continue_book_btn.click()
                            logging.info(f"当前时间：{datetime.datetime.now()}, 时段 {order_time['time']}: 成功预订 {need_count} 张票")
                            order_times.remove(order_time)  # 从原列表删除
                        else:
                            # 只能预订部分
                            timezone_select.select_by_value(str(slots_int))
                            remaining = need_count - slots_int
                            order_time['count'] = str(remaining)
                            logging.info(f"当前时间：{datetime.datetime.now()}, 时段 {order_time['time']}: 预订 {slots_int} 张票，还需 {remaining} 张")
                    else:
                        logging.info(f"当前时间：{datetime.datetime.now()}, 时段 {order_time['time']}: 无余票")

                if len(order_times) == 0:
                    task_done = True
                else:
                    refresh_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "refreshSlots_" + select_date_input))
                    )
                    refresh_btn.click()
                    time.sleep(fresh_frequency)

        logging.info("All booking tasks completed")

    except Exception as e:
        error_msg = str(e)
        if "invalid session id" in error_msg or "session deleted" in error_msg:
            logging.info("浏览器已关闭，任务结束")
        else:
            logging.error(f"Automation task error: {error_msg}")
            raise
    finally:
        if driver:
            time.sleep(5)
            driver.quit()  # Close or not based on requirements
            os._exit(0)  # 退出Python进程


# ==================== Start Service ====================
def open_browser():
    """自动打开浏览器"""
    import webbrowser
    import time
    time.sleep(1.5)  # 等待Flask完全启动
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == "__main__":
    logging.info("Starting Flask service...")

    # 在新线程中打开浏览器
    threading.Thread(target=open_browser, daemon=True).start()

    # 启动Flask
    app.run(debug=False, port=5000)  # 生产环境关闭debug