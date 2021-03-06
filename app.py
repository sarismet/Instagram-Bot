from selenium import webdriver
from time import sleep
import os
from webdriver_manager.chrome import ChromeDriverManager
import lists
import sys
import json
import smtplib
import re
import psycopg2

from lists import except_list

from secrets import *
from email.message import EmailMessage

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType

class InstaApi:
    def __init__(self):

        print("Initializing ...", file=sys.stdout)
        self.driver = webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())
        
        self.username = username
        self.password = password
        self.report = ""
        self.treators = []
        self.treatorNominees = {}
        self.runTimes = 0
        self.pendingRequest = []
        self.db = psycopg2.connect( database_url, sslmode='require')
        self.c = self.db.cursor()

    def __enter__(self):

        self.report = self.report + "username is : " + self.username + "\n"
        self.report = self.report + "limit of pending is : " + str(
            limit_of_pending) + "\n"
        self.report = self.report + "runtime_limit is : " + str(
            runtime_limit) + "\n"
        self.report = self.report + "ban_limit is : " + str(ban_limit) + "\n"

        treator_nominees = """CREATE TABLE IF NOT EXISTS Treatornominees(
        username VARCHAR(200) NOT NULL,
        value INT,
        PRIMARY KEY (username)
        );"""
        self.c.execute(treator_nominees)
        run_times = """CREATE TABLE IF NOT EXISTS RunTimes(
                total_run_times INT
                );"""
        self.c.execute(run_times)
        banned_users = """CREATE TABLE IF NOT EXISTS BannedUsers(
                username VARCHAR(200) NOT NULL,
                PRIMARY KEY (username)
                );"""
        self.c.execute(banned_users)
        self.db.commit()
        self.c.execute(
            "SELECT * FROM Treatornominees ORDER BY value DESC,value DESC;")

        rows = self.c.fetchall()
        self.db.commit()
        for row in rows:
            self.treatorNominees[row[0]] = row[1]
        self.c.execute("select * from Runtimes;")
        rows = self.c.fetchall()
        self.db.commit()

        self.runTimes = rows[0][0]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Closing Driver ...", file=sys.stdout)
        self.driver.close()
        self.sendMail()

    def sendMail(self):
        msg = EmailMessage()
        msg['Subject'] = 'instagram api self.report'
        msg['From'] = user_email
        msg['To'] = email_to
        msg.set_content(self.report)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(user_email, user_email_password)
            smtp.send_message(msg)

    def bringTheAction(self):
        
        if self.runTimes > runtime_limit:
            followers_results = self.get_followers()
            if not followers_results[0]:
                return None
            followers = followers_results[1]
            sleep(3)
            following_results = self.get_following()
            if not following_results[0]:
                return None
            followings = following_results[1]

            self.report = self.report + "you have " + str(
                len(followers)) + " followers.\n"
            self.report = self.report + "you follow " + str(
                len(followings)) + "users.\n\n"

            print("followings are ",followings)
            print("followers are ",followers)
            for user in followings:
                print("following user ",user)
                if user not in followers and user not in except_list:
                    print("This user named "+user+" is not following you even if you follow him or her")
                    self.report = self.report + "The user : " + user + "is not following you even if you follow her/him!!!\n"
                    self.treators.append(user)

            self.c.execute("UPDATE Runtimes SET total_run_times = 0;")
            self.db.commit()
        else:
            self.c.execute(
                "UPDATE Runtimes SET total_run_times = total_run_times + 1")
            self.db.commit()
        
        get_pending_friend_request_results = self.get_pending_friend_request()
        if not get_pending_friend_request_results[0]:
            return None
        self.pendingRequest = get_pending_friend_request_results[1]
        print("There are " + str(len(self.pendingRequest)) +
              " pending friend requests",
              file=sys.stdout)
        self.report = self.report + "There are " + str(len(
            self.pendingRequest)) + " pending friend requests.\n"
        for count, name in enumerate(self.treatorNominees, 0):
            print("treator nominee is ",name, "and its count is ",self.treatorNominees[name])
            if name not in self.pendingRequest:
                self.treators.append(name)
            elif self.treatorNominees[
                    name] > limit_of_pending and count < ban_limit:
                print("I am in else if part count is ",count, "name is ",name)
                if name not in except_list:
                    self.treators.append(name)
            else:
                print("I am in else part. limit_of_pending ", limit_of_pending, "ban limit ",ban_limit, "runtime_limit ",runtime_limit)
                self.c.execute(
                    "UPDATE Treatornominees SET value = value + 1 WHERE username = %s;",
                    (name, ))
                self.db.commit()
        for user in self.pendingRequest:
            if user not in self.treatorNominees.keys():
                print("user ",
                      user,
                      " is not in treator nominee",
                      file=sys.stdout)
                self.report = self.report + "user " + user + " is not in treator nominee so the user" + user + "id added.\n"
                self.c.execute(
                    "INSERT INTO Treatornominees (username,value) VALUES (%s,%s);",
                    (user, 1))
                self.db.commit()
        self.report = self.report + "Treators are :\n"
        print("treators are ")
        for treator in self.treators:
            print(treator)
            self.report = self.report + str(treator) + "\n"

        for user in self.treators:
            sleep(5)

            keep_going = True
            index = 0
            completed = False
            while keep_going and index < 3:
                index += 1
                try:
                    self.report = self.report + "trying to block " + user + "\n"
                    keep_going = self.block_user(user)
                    print("the user ", user, " is blocked\n", file=sys.stdout)
                    self.report = self.report + "the user " + user + " is blocked. URL is "+" https://www.instagram.com/"+user+"/"
                    try:
                        self.c.execute(
                            "DELETE FROM Treatornominees WHERE username = %s ;",
                            (user, ))
                        self.db.commit()
                        completed = True
                        self.c.execute(
                            "INSERT INTO BannedUsers (username) VALUES (%s);",(user,)
                        )
                        self.db.commit()
                    except Exception as e:
                        self.report = self.report + "there is an error as deleting the user from the database \n"
                        print("error in database part part \n ",
                              e,
                              " has occurred\n",
                              file=sys.stdout)
                    break
                except Exception as e:
                    
                    print("An error as ",e,"occurred so the user ",
                          user,
                          " is not blocked retrying...\n",
                          file=sys.stdout)
            if not completed:
                self.report = self.report + "the user " + user + " is not blocked after 3 tries so we give up blocking it"
                self.c.execute(
                    "DELETE FROM Treatornominees WHERE username = %s ;",
                    (user, ))
                self.db.commit()

    def login(self, sleep_time=3):
        print("login", file=sys.stdout)
        self.driver.get("https://www.instagram.com")
        sleep(sleep_time)
        try:
            self.driver.find_element_by_name('username').send_keys(
                self.username)
            self.driver.find_element_by_name('password').send_keys(
                self.password)
            
            button_to_click = None
            buttons = self.driver.find_element_by_class_name("HmktE").find_elements_by_tag_name("button")
            for button in buttons:
                if button.text == "Log In":
                    button_to_click = button
                    break
            button_to_click.click()
        except Exception as e:
            print("Error as e ",e)
            self.report = self.report + "There is an error in username-password login page.\n"
            return False
        sleep(sleep_time)
        try:
            self.driver.find_elements_by_class_name("cmbtv").find_element_by_tag_name("button").click()
        except:
            try:
                self.driver.find_element_by_xpath(
                    "//button[contain(text(), 'Not Now')]").click()
            except:
                self.report = self.report + "First Not Know is not working\n"
        sleep(sleep_time)
        try:
            buttons = self.driver.find_elements_by_class_name("mt3GC").find_element_by_tag_name("button")
            button_to_click = None
            for button in buttons:
                if button.text == "Not Now":
                    button_to_click = button
            button_to_click.click()
        except:
            try:
                self.driver.find_element_by_xpath(
                    "//button[contain(text(), 'Not Now')]").click()
            except:
                self.report = self.report + "Second Not Know is not working\n"
        sleep(sleep_time)
        return True

    def get_followers(self, sleep_time=3):
        print("getting followers", file=sys.stdout)
        user_link = "https://www.instagram.com/{}/".format(self.username)
        self.driver.get(user_link)
        arr = []
        sleep(sleep_time)
        href="/{}/followers/".format(self.username)
        follower_number_element = self.driver.find_element_by_xpath('//a[@href="'+href+'"]')
        try:
            follower_number_element.click()
        except Exception as e:
            print("get followers in stage 1 returns error")
            self.report = self.report + str(e) + "occured !!! \n"
            return (False, [])
        sleep(sleep_time)
        names_links_list = None
        all_names_links_list = None
        try:
            all_names_links_list = self.driver.find_element_by_class_name("isgrP")
        except Exception as e:
            print("get followers in stage 2 returns error")
            self.report = self.report + str(e) + "occured !!! \n"
            return (False, [])
        sleep(sleep_time)
        head, tail = 0, 1
        index = 1
        while head != tail:
            print("while ",index)
            index = index + 1
            head = tail
            tail = self.driver.execute_script(
                "arguments[0].scrollTo(0,arguments[0].scrollHeight); return arguments[0].scrollHeight;",
                all_names_links_list)
            sleep(sleep_time)
        names_links_list = all_names_links_list.find_element_by_class_name("PZuss")
        names = names_links_list.find_elements_by_tag_name('a')
        name_list = [name for name in names if name.text != ""]
        for name in name_list:
            arr.append(name.text)

        print(len(arr),
              "users follow you and these are",
              arr,
              "\n",
              file=sys.stdout)
        
        try:
            follower_number = int(re.sub(" followers","",follower_number_element.text))
            if len(arr) != follower_number:
                print("size does not match in followers")
                print("numbers do not match")
                print("follower_number is ",follower_number ," and the size of array is ",len(arr))
                return (False, [])
        except Exception as e:
            return (False, [])
        print("returning true in followers")
        return (True, arr)

    def get_following(self, sleep_time=7):
        print("getting followings", file=sys.stdout)
        user_link = "https://www.instagram.com/{}/".format(self.username)
        self.driver.get(user_link)
        sleep(sleep_time)
        arr = []
        href="/{}/following/".format(self.username)
        follower_number_element = self.driver.find_element_by_xpath('//a[@href="'+href+'"]')
        try:
            follower_number_element.click()
        except Exception as e:
            self.report = self.report + str(e) + "occured. !!! \n"
            return (False, [])

        sleep(sleep_time)
        names_links_list = None
        all_names_links_list = None
        try:
            all_names_links_list = self.driver.find_element_by_class_name("isgrP")
        except Exception as e:
            self.report = self.report + str(e) + "occured. !!! \n"
            return (False, [])
        sleep(sleep_time)
        head, tail = 0, 1
        while head != tail:
            head = tail
            tail = self.driver.execute_script(
                "arguments[0].scrollTo(0,arguments[0].scrollHeight); return arguments[0].scrollHeight;",
                all_names_links_list)
            sleep(sleep_time)
        names_links_list = all_names_links_list.find_element_by_class_name("PZuss")
        names = names_links_list.find_elements_by_tag_name('a')
        name_list = [name for name in names if name.text != ""]
        for name in name_list:
            arr.append(name.text)

        print("you follow",
              len(arr),
              "users abnd these are ",
              arr,
              file=sys.stdout)        

        try:
            follower_number = int(re.sub(" following","",follower_number_element.text))
            if len(arr) != follower_number:
                print("numbers do not match")
                print("follower_number is ",follower_number, " and the size of array is ",len(arr))
                return (False, [])
        except Exception as e:
            print("ERRRORRRRR ",e)
            return (False, [])
        print("Returning arr in following is ",arr)
        return (True, arr)

    def block_user(self, username):
        print("blocking user", username, "...", file=sys.stdout)
        user_link = "https://www.instagram.com/{}/".format(username)
        self.driver.get(user_link)
        sleep(3)
        try:
            
            self.driver.find_element_by_class_name('AFWDX').find_element_by_tag_name('button').click()
        except Exception as e:
            print("Error occurred as e",e)
            return False
        sleep(3)
        try:
            buttons = self.driver.find_element_by_class_name('mt3GC').find_elements_by_tag_name('button')
            button_to_click = None
            for button in buttons:
                if button.text == "Block this user":
                    button_to_click = button
                    break
            button_to_click.click()
        except Exception as e:
            print("Error occurred as e",e)
            return False
        sleep(3)
        try:
            buttons = self.driver.find_element_by_class_name('mt3GC').find_elements_by_tag_name('button')
            button_to_click = None
            for button in buttons:
                if button.text == "Block":
                    button_to_click = button
                    break
            button_to_click.click()
        except Exception as e:
            print("Error occurred as e",e)
            return False
        sleep(3)
        try:
            self.driver.find_element_by_class_name('mt3GC').find_element_by_tag_name('button').click()
        except Exception as e:
            print("Error occurred as e",e)
            return False
        print("the user", username, "is banned", file=sys.stdout)

        return True

    def get_pending_friend_request(self, sleep_time=5):
        user_link = "https://www.instagram.com/{}/".format(self.username)
        self.driver.get(user_link)
        print("getting the pending friend request", file=sys.stdout)
        sleep(sleep_time)
        try:
            print("Tring to click Setting button", file=sys.stdout)
            self.driver.find_element_by_class_name("wpO6b  ").click()
        except Exception as e:
            self.report = self.report + "Setting Button is not clicked. Exiting!!! \n"
            print("Setting Button is not clicked error is ",e, file=sys.stdout)
            return (False, [])
        sleep(sleep_time)
        try:
            print("Tring to click account data button", file=sys.stdout)
            buttons = self.driver.find_element_by_class_name('mt3GC').find_elements_by_tag_name('button')
         
            element_to_click = None
            for button in buttons:

                if button.text == "Privacy and Security":
                    element_to_click = button
                
            element_to_click.click()
            
        except Exception as e:
            self.report = self.report + "Security Button is not clicked. Exiting!!! \n"
            print("Security Button is not clicked. error is ",e, file=sys.stdout)
            return (False, [])
        sleep(sleep_time)
        try:
            print("Tring to click account data button", file=sys.stdout)
            href="/accounts/access_tool/"
            self.driver.find_element_by_xpath('//a[@href="'+href+'"]').click()
        except:
            print("See account data button is not clicked", file=sys.stdout)
            self.report = self.report + "See account data button is not clicked. Exiting!!! \n"
            return (False, [])
        sleep(sleep_time)
        try:
            print("Tring to click pending request button", file=sys.stdout)
            
            href="/accounts/access_tool/current_follow_requests"
            self.driver.find_element_by_xpath('//a[@href="'+href+'"]').click()
        except Exception as e:
            print("See pending request button is not clicked. Error is ",e, file=sys.stdout)
            self.report = self.report + "See pending request button is not clicked. Exiting!!! \n"
            return (False, [])

        sleep(sleep_time)
        index = 0
        while True:
            sleep(sleep_time)
            print("in while for ",index, "times")
            index = index + 1
            try:
                self.driver.find_element_by_class_name('PVkFi').find_element_by_tag_name('button').click()
                print("There is more", file=sys.stdout)
            except Exception as e:
                print("Error as ",e)
                break
        print("Getting the list...", file=sys.stdout)
        sleep(sleep_time)
        names = self.driver.find_elements_by_class_name("-utLf")
        name_list = [name.text for name in names if name.text != ""]
        print("The list is gotten", file=sys.stdout)
        return (True, name_list)


with InstaApi() as app:
    if app.login():
        app.bringTheAction()
