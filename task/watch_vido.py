# Copyright (c) 2025 Mortal004
# Copyright (c) 2026 Henry
# All rights reserved.
# This software is provided for non-commercial use only.
# For more information, see the LICENSE file in the root directory of this project.
import json
import os
import random
import tempfile
from selenium.common import  NoAlertPresentException
import time

from selenium.webdriver.common.action_chains import ActionChains

from task.DeepSeekAsk import DeepSeekAsk
from task.tool import color
import pyautogui
from selenium.webdriver.common.by import By
import itertools

b = 0
pause_start_time = 0.0


def _atomic_write_account_info(data, path=r'task/tool/account_info.json'):
    """原子写入 account_info.json：临时文件 + os.replace，避免中途崩溃截断配置。"""
    dir_name = os.path.dirname(path) or '.'
    fd, tmp_path = tempfile.mkstemp(prefix='.account_info.', suffix='.tmp', dir=dir_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fil:
            json.dump(data, fil)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def generate_combinations_list(input_list):
    """
    返回列表形式的组合，完整组合放在第一位
    """
    n = len(input_list)

    if n == 3:
        # 三者都出现的情况（放在第一位）
        triple = [input_list.copy()]
        # 两两组合的所有可能
        pairs = [list(combo) for combo in itertools.combinations(input_list, 2)]
        return triple + pairs

    elif n == 4:
        # 取四个元素的情况（放在第一位）
        quadruple = [input_list.copy()]
        # 取三个元素的所有可能
        pairs = [list(combo) for combo in itertools.combinations(input_list, 2)]
        triples = [list(combo) for combo in itertools.combinations(input_list, 3)]
        return quadruple + triples + pairs
    else:
        return [input_list]

def check_internet(driver):
    try:
        internet_choice=driver.find_element(By.CSS_SELECTOR,"[class='ans-vjserrdisplay-opts']")
        # print(color.red('网络异常'), flush=True)
        choice_list=internet_choice.find_elements(By.CSS_SELECTOR,"[name='ans-vjserrdisplay-opt']")
        for choice in choice_list:
            choice.click()
    except Exception:
        pass

def get_answer(API,question,typ):
    answer = []
    try:
        answer = DeepSeekAsk(API, question, typ)
    except Exception as e:
        print(f'答题时出错了{e}',flush=True)
    return answer
def finish_video_question(options_txt,options,answer,question_type):
    answer_num = []
    option_num = 0
    if question_type == '单选题' or question_type == '判断题':
        for option in options_txt:
            if answer[0] in option:
                break
            option_num += 1
        answer_num.append(option_num)
    elif question_type == '多选题':
        if len(answer) == 1:
            lst = answer[0]
        else:
            lst = answer
        for option in options_txt:
            for ans in lst:
                if ans in option:
                    answer_num.append(option_num)
            option_num += 1
        answer_num = list(set(answer_num))
    # 点击正确答案
    for ans in answer_num:
        checked=options[ans].find_elements(By.CSS_SELECTOR,'[checked="checked"]')
        if not checked:
            options[ans].click()
            time.sleep(1)
        else:
            print(color.yellow(f'已选择选项{ans}'), flush=True)
            continue
def check_video_question(driver,API,video_title_choice):
    try:
        element=driver.find_element(By.CLASS_NAME,'tkTopic')
        print(color.yellow('已检测到视频中有题目'), flush=True)
        question_title = element.find_element(By.CLASS_NAME, 'tkItem_title').text
        try:
            question_type=element.find_element(By.CLASS_NAME,'tkTopic_type').text
        except Exception:
            question_type=element.find_element(By.CLASS_NAME,'tkTopic_title').text
        options = element.find_element(By.CLASS_NAME, 'tkItem_ul')
        options = options.find_elements(By.TAG_NAME, 'li')
        options_txt=[option.text for option in options]
        submit = element.find_element(By.ID, 'videoquiz-submit')
        if video_title_choice=='DeepSeek AI':
            answer = get_answer(API,question_title+'\n'+str(options_txt),question_type)
            # answer=['A']
            # print(answer, flush=True)
            if type(answer) is str:
                answer = eval(answer)
            if not answer:
                print(color.red(f'❌ 答题失败'), flush=True)
                return
            else:
                finish_video_question(options_txt,options,answer,question_type)
                submit.click()
        else:
            try:
                if question_type=='单选题' or question_type=='判断题':
                    for option in options:
                        option.click()
                        #提交
                        submit.click()
                elif question_type=='多选题':
                    answer_lost=generate_combinations_list(options)
                    last_ans_set=set()
                    for answer in answer_lost:
                        now_ans_set=set(answer)
                        # 使用 ^ 运算符计算对称差集
                        different_elements = now_ans_set ^ last_ans_set
                        for option in different_elements:
                            option.click()
                        last_ans_set=now_ans_set
                        #提交
                        submit.click()
            except Exception:
                pass
        try:
            return_video=driver.find_element(By.CSS_SELECTOR, '[class="bntWhiteBorder ans-videoquiz-back fr"]')
            return_video.click()
        except Exception:
            pass
        #继续学习
        try:
            continue_learn=element.find_element(By.ID,'videoquiz-continue')
            continue_learn.click()
        except Exception:
            pass
    except Exception:
        return

def check_vido_play(driver, last_time, current_time):
    global b, pause_start_time
    # 添加随机延迟，打破规律性检测
    time.sleep(random.uniform(0.3, 0.8))

    # 忽略无效时间（如视频还没真正开始播放，current_time 是 0:00 或空）
    if current_time == '' or current_time == '0:00' or current_time == '00:00':
        pause_start_time = time.time()
        b = 0
        return

    with open(r'task/tool/account_info.json', 'r', encoding='utf-8') as f:
        account_info = json.load(f)
        speed = account_info['speed']
    if last_time == current_time and current_time != '':
        pause_duration = time.time() - pause_start_time
        b += 1
        if pause_duration >= 2 and b != 3:
            try:
                print(color.red(f'当前视频播放被暂停,点击继续播放'), flush=True)
                # 方法1：尝试常规点击
                try:
                    play_btn = driver.find_element(By.CSS_SELECTOR,
                        '[class="vjs-play-control vjs-control vjs-button vjs-paused"]')
                    offset_x = random.randint(-3, 3)
                    offset_y = random.randint(-2, 2)
                    action = ActionChains(driver)
                    action.move_to_element_with_offset(play_btn, offset_x, offset_y).pause(
                        random.uniform(0.1, 0.3)).click().perform()
                except Exception:
                    pass
                # 方法2：如果常规点击无效，使用JS直接播放（绕过检测）
                time.sleep(0.3)
                try:
                    driver.execute_script("""
                        var videos = document.querySelectorAll('video');
                        for(var i=0; i<videos.length; i++) {
                            if(videos[i].paused && videos[i].src) {
                                videos[i].play().catch(function(e){});
                            }
                        }
                    """)
                except Exception:
                    pass
                time.sleep(random.uniform(1.5, 2.5))
            except Exception:
                print(color.red(f'点击失败'), flush=True)
            pause_start_time = time.time()
        elif b == 3 and int(speed) >= 2:
            try:
                if int(speed) > 2:
                    print(color.red(f'当前视频已被设置不能调节高倍数，现在将倍数调至2倍'), flush=True)
                    new_speed = 2
                    account_info['speed'] = '2'
                else:
                    new_speed = 1
                    print(color.red(f'当前视频已被设置不能调节高倍数，现在将倍数调至1倍'), flush=True)
                    account_info['speed'] = '1'
                for j in range(int(int(speed) - new_speed) * 10):
                    # 模拟人类打字节奏，添加随机延迟
                    pyautogui.press('a')
                    action = ActionChains(driver)
                    action.send_keys('a').perform()
                    time.sleep(random.uniform(0.15, 0.25))
                print(color.green('调节成功'), flush=True)
                time.sleep(random.uniform(0.5, 1.0))
                try:
                    play_btn = driver.find_element(By.CSS_SELECTOR,
                        '[class="vjs-play-control vjs-control vjs-button vjs-paused"]')
                    offset_x = random.randint(-3, 3)
                    offset_y = random.randint(-2, 2)
                    action = ActionChains(driver)
                    action.move_to_element_with_offset(play_btn, offset_x, offset_y).pause(
                        random.uniform(0.1, 0.3)).click().perform()
                except Exception:
                    print(color.yellow(f'点击播放失败'), flush=True)
            except Exception:
                pass
            _atomic_write_account_info(account_info)
            # 重置计数器，避免重复触发降速逻辑
            pause_start_time = time.time()
            b = 0
        elif b == 3 and int(speed) == 1:
            raise Exception('视频播放异常')
    else:
        pause_start_time = time.time()
        b = 0
def handle_video_error_alert(driver):
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        if "视频播放异常" in alert_text:
            print(color.red("检测到视频播放异常弹窗，尝试刷新页面..."))
            alert.accept()
            time.sleep(2)
            driver.refresh()
            # 刷新后需要重新进入 iframe，具体逻辑根据实际情况补充
            raise Exception('视频播放异常')
        else:
            alert.accept()
            raise Exception('视频播放异常')
    except NoAlertPresentException:
        return
def check_vido_finish(driver,i,time_start,total_time,vido_iframe,lock_screen,API,video_title_choice):
    last_time = 0
    h = 0
    video_start_verified = False  # 标记视频是否真正开始播放
    # 判断是否完成任务
    while True:
        # 随机化检测间隔，模拟人类不规律的行为
        time.sleep(random.uniform(0.8, 1.5))
        driver.switch_to.default_content()
        driver.switch_to.frame('iframe')
        elements2 = driver.find_elements(By.CLASS_NAME, 'ans-job-icon-clear ')
        element2 = elements2[i]
        parent_element2 = element2.find_element(By.XPATH, "..")
        parent_element2_class = parent_element2.get_attribute("class")
        txt = element2.get_attribute('aria-label')
        if txt == '任务点已完成' or 'ans-attach-ct ans-job-finished' in parent_element2_class:
            print(color.green(f'已完成第{i + 1}个视频'), flush=True)
            time_end = time.time()
            print(color.green('总共耗费了%.2f秒.' % (time_end - time_start)), flush=True)
            break
        else:
            driver.switch_to.default_content()
            driver.switch_to.frame('iframe')
            driver.switch_to.frame(vido_iframe)
            # 模拟真实用户：偶尔移动鼠标、滚动页面
            if random.random() < 0.15:
                pyautogui.move(random.randint(-100, 100), random.randint(-50, 50))
                pyautogui.scroll(random.randint(-3, 3))
            check_internet(driver)
            check_video_question(driver, API, video_title_choice)
            element = driver.find_element(By.CLASS_NAME, 'vjs-current-time-display')
            current_time = element.text

            # 验证视频是否真正在播放
            if not video_start_verified and current_time != '0:00' and current_time != '00:00' and current_time != '':
                print(color.green(f'视频已开始播放，当前进度: {current_time}'), flush=True)
                video_start_verified = True

            # 如果视频还没开始播放（超过10秒还是0:00），尝试重新点击播放
            if not video_start_verified and h == 0:
                try:
                    driver.execute_script("""
                        var videos = document.querySelectorAll('video');
                        for(var v of videos) {
                            if(v.src && v.paused) {
                                console.log('视频暂停中，尝试播放');
                                v.play().catch(()=>{});
                            }
                        }
                    """)
                except Exception:
                    pass

            check_vido_play(driver, last_time, current_time)
            last_time = current_time
            if current_time == total_time:
                if h == 0:
                    h += 1
                    try:
                        print(color.yellow('视频已播放完毕，但任务点仍未完成，开始重播'), flush=True)
                        driver.find_element(By.CSS_SELECTOR,
                                            '[class="vjs-play-control vjs-control vjs-button vjs-paused vjs-ended"]').click()
                    except Exception:
                        print(color.red(f'点击失败'), flush=True)
                else:
                    print(color.green(f'已完成第{i + 1}个视频'), flush=True)
                    time_end = time.time()
                    print(color.green('总共耗费了%.2f秒.' % (time_end - time_start)), flush=True)
                    break
            if lock_screen:
                # 随机化锁屏鼠标移动，不要每次都移动同样的距离
                offset = random.randint(10, 30)
                pyautogui.move(offset, 0)
                pyautogui.move(-offset, 0)
    return True

def study_page(driver,course_name,lock_screen,API,video_title_choice):
    cond=False
    driver.switch_to.default_content()
    driver.switch_to.frame('iframe')
    try:
        # 判断是否完成任务
        elements1 = driver.find_elements(By.CLASS_NAME, 'ans-job-icon-clear ')
        print(color.magenta(f'已检测到{len(elements1)}个视频包含有任务点'),flush=True)
    except Exception:
        pyautogui.scroll(-250)
        print(color.green('视频已完成,点击下一节'),flush=True)
        return

    for i in range(len(elements1)):
        element1=elements1[i]
        # 定位到该元素的上一级（父元素）
        parent_element = element1.find_element(By.XPATH, "..")
        try:
            # 获取 parent_element 的class值
            parent_element_class=parent_element.get_attribute("class")
            txt = element1.get_attribute('aria-label')
        except Exception:
            txt = ''
            parent_element_class=''
        if txt == '任务点未完成' and 'ans-attach-ct' in parent_element_class:
            vido_iframe = element1.find_element(By.XPATH, "following-sibling::iframe[1]")
            driver.execute_script("arguments[0].scrollIntoView();", vido_iframe)
            driver.switch_to.frame(vido_iframe)
            print(color.green(f'开始播放第{i + 1}个视频'), flush=True)
            time_start = time.time()

            # 先检查是否有"我知道了"弹窗要先关闭
            try:
                element = driver.find_element(By.CLASS_NAME, 'writeNote_vid_blue')
                action = ActionChains(driver)
                action.move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()
                time.sleep(0.5)
            except Exception:
                pass

            # 点击播放
            try:
                big_play_btn = driver.find_element(By.CLASS_NAME, 'vjs-big-play-button')
                action = ActionChains(driver)
                action.move_to_element(big_play_btn).pause(random.uniform(0.2, 0.5)).click().perform()
            except Exception:
                pass

            # 等待视频实际开始播放
            time.sleep(2)

            # 用JS确保视频在播放
            try:
                driver.execute_script("""
                    var videos = document.querySelectorAll('video');
                    for(var v of videos) {
                        if(v.paused && v.src) {
                            v.play().catch(()=>{});
                        }
                    }
                """)
            except Exception:
                pass

            # 调节音量
            try:
                print(color.blue('调节音量'), flush=True)
                element = driver.find_element(By.XPATH, '//*[@id="video"]/div[6]/div[6]')
                action = ActionChains(driver)
                action.move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()
                print(color.green('调节成功'), flush=True)
            except Exception:
                print(color.yellow('未找到音量，或已经调节'), flush=True)
            time.sleep(random.uniform(0.5, 1.0))
            element = driver.find_element(By.CLASS_NAME, 'vjs-duration-display')
            total_time = element.text
            if  total_time=='' or total_time=='0:00':
                print(color.red('获取视频总时长失败'),flush=True)
                total_time='1'
            else:
                print(color.green(f'该视频总时长为：{total_time}'),flush=True)
            print(color.yellow('请不要将窗口最小化，这有可能导致脚本异常\n视频播放完毕会自动跳转\n正在观看视频中……'),flush=True)
            driver.switch_to.default_content()
            driver.switch_to.frame('iframe')
            b = 0
            pause_start_time = 0  # 添加变量记录暂停开始时间
            check_vido_finish(driver,i,time_start,total_time,vido_iframe,lock_screen,API,video_title_choice)
            cond=  True
        driver.switch_to.default_content()
        # check_face(driver,driver.current_url,'popDiv1 wid640  faceCollectQrPopVideo  popClass faceRecognition_0')
        driver.switch_to.frame('iframe')
    print(color.green('所有视频均已完成'),flush=True)
    if cond and judge_active(driver):
        save_vido(driver,course_name)
        print(color.green('已保存视频观看记录'),flush=True)
    return

def save_vido(driver,course_name):
    driver.switch_to.default_content()
    element = driver.find_element(By.CLASS_NAME, 'prev_title')
    title = element.get_attribute('title')
    try:
        f = open(fr'task\record\《{course_name}》的刷课记录.txt', 'a', encoding='utf-8')
        f.write(
            f'已刷完:《{title}》章节中的所有视频\n完成时间：{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}\n\n')
    except Exception:
        pass

def judge_active(driver):
    driver.switch_to.default_content()
    element=driver.find_element(By.CSS_SELECTOR, '[class="prev_ul clearfix"]')
    elements = element.find_elements(By.CSS_SELECTOR, '[title="视频"]')
    num=len(elements)
    try:
        txt=elements[num-1].get_attribute('class')
    except IndexError:
        txt = 'active'
    if txt=='active':
        return True
    else:
        return False

