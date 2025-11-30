import os
import io
import json
import math
import time
import requests
#import random
from datetime import datetime
from loguru import logger
from PIL import Image
from concurrent import futures
from viewing import view

# 处理原始数据,去掉一些无用信息, 让数据更整齐
def ProcessRawData(RawData):
    NewData = {}
    for i in RawData.values():
        media = {
            "id": i['id'],
            "BV": i['bv_id'],
            "是否失效": False,
            "up主": {
                "ID": i['upper']['mid'],
                "昵称": i['upper']['name'],
                "头像": i['upper']['face']
            },
            "视频信息": {
                "标题": i['title'],
                "封面": i['cover'],
                "简介": i['intro'],
                "时长": time.strftime("%H:%M:%S", time.gmtime(i['duration']))
            },
            "观众数据": {
                "播放量": i['cnt_info']['play'],
                "收藏量": i['cnt_info']['collect'],
                "弹幕数量": i['cnt_info']['danmaku']
            },
            "三个时间": {
                "上传时间": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(i['ctime'])),
                "发布时间": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(i['pubtime'])),
                "收藏时间": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(i['fav_time']))
            }
        }
        NewData[media['id']] = media
    return NewData


# 与上一次爬取对比, 对于被删除的和自己取消收藏的视频,予以不同的标记
def CompareLastTime(ReadPath, NewData):
    if not os.path.exists(ReadPath):
        return NewData
    with open(ReadPath, 'r', encoding='utf-8') as f:
        OldData = json.load(f)
    # 视频被删除, 则保留上次的数据, 并且标记
    for i in list(NewData.values()):
        if i['视频信息']['标题'] == "已失效视频" and str(i['id']) in OldData.keys():
            logger.info('{}失效了'.format(OldData[str(i['id'])]['视频信息']['标题']))
            OldData[str(i['id'])]['是否失效'] = True
            NewData[str(i['id'])] = OldData[str(i['id'])]

    # 自己取消收藏, 标记
    for i in list(OldData.values()):
        if i['id'] not in NewData.keys():
            logger.info('{}取消了收藏'.format(i['视频信息']['标题']))
            OldData[str(i['id'])]['是否取消了收藏'] = True
            NewData[str(i['id'])] = OldData[str(i['id'])]

    return NewData


# 爬取收藏夹的ID
def GetFavoriteID(WritePath, UID):
    # 请求头
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
    }
    url = 'https://api.bilibili.com/x/v3/fav/folder/created/list-all'
    params = {
        'up_mid': UID,  # 自己账号的UID
        'jsonp': 'jsonp',
    }
    response = requests.get(url=url, params=params, headers=headers)
    assign = response.json()

    with open(os.path.join(WritePath, '收藏夹id.json'), 'w', encoding='utf-8') as fp:
        json.dump(assign, fp, ensure_ascii=False)
    logger.info('收藏夹id爬取成功')


# 爬取一个收藏夹信息, Media_Id代表收藏夹, MaxPage代表收藏夹的页数
def GetOneFavorite(Media_Id, MaxPage):
    # 爬虫的参数, 其中params里的pn（页数）会随着遍历的改变而改变
    url = 'https://api.bilibili.com/x/v3/fav/resource/list'
    params = {
        'ps': 20,
        'keyword': '',
        'order': 'mtime',
        'type': 0,
        'tid': 0,
        'platform': 'web',
        'jsonp': 'jsonp',
        'pn': 1,
        'media_id': Media_Id
    }
    headers = {
        'authority': 'api.bilibili.com',
        'method': 'GET',
        'path': '/x/v3/fav/resource/list?media_id=309076131&pn=1&ps=20&keyword=&order=mtime&type=0&tid=0&platform=web&jsonp=jsonp',
        'scheme': 'https',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        # 'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'max-age=0',
        'cookie': "_uuid=F500E27C-018D-CC3F-17E8-C64812E174DA08613infoc; buvid3=475B7DAC-0579-421B-85B7-07A4076090B734771infoc; buvid_fp=475B7DAC-0579-421B-85B7-07A4076090B734771infoc; CURRENT_FNVAL=80; blackside_state=1; rpdid=|(k|k)~~RkkJ0J'uYk|YumRkm; fingerprint3=c1d980f375c848a729ebdd130960a847; CURRENT_QUALITY=112; LIVE_BUVID=AUTO9716210898194009; fingerprint_s=be57440a1cba44ed342ad526646463d4; bp_t_offset_51541144=529073781132033226; bp_video_offset_51541144=529330083309673464; bp_t_offset_289920431=529693188424888145; fingerprint=a43248e91a776fba5e92af41d1a900e0; buvid_fp_plain=95AEE299-5E58-4AA1-92EF-CFE2BE6C6243184999infoc; SESSDATA=41ff3c64%2C1637735786%2Cff017%2A51; bili_jct=c0a63b68e972a8d1acc44a3718075b58; DedeUserID=289920431; DedeUserID__ckMd5=c43d13bc962635fe; sid=bvgle9dv; PVID=3; bp_video_offset_289920431=529757320878990660; bfe_id=5db70a86bd1cbe8a88817507134f7bb5",
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
    }

    data = {}
    # 遍历爬取一个收藏夹的不同页数, 然后合并到一个字典里
    for params['pn'] in range(MaxPage)[1::]:
        #logger.info(f"第{str(params['pn'])}页")

        j: int = 0
        while 1:
            try:
                response = requests.get(url=url, params=params, headers=headers).json()
                break
            except:
                j += 1
                print(f"第{str(params['pn'])}页爬取失败, 重试中[{j}]...", end='\r')
                if j == 1:
                    logger.error(f"第{str(params['pn'])}页爬取失败, 重试中...")
                continue
        if j == 0:
            logger.info(f'第{str(params['pn'])}页爬取成功')
        else:
            print(f'第{str(params['pn'])}页爬取成功, 共重试{j}次                ')
            logger.warning(f'第{str(params['pn'])}页爬取成功, 共重试{j}次')
        #time.sleep(random.random())
        medias_list = response['data']['medias']
        # 将不同页数合并到字典里
        for i in medias_list:
            data[i['id']] = i
    return data


# 爬取全部收藏夹信息
def GetALLFavorite(id_path, WritePath):
    # 打开文件, 获取之前爬取到的收藏夹id和收藏夹页数
    with open(os.path.join(id_path, '收藏夹id.json'), 'r', encoding='utf-8') as fp:
        file = json.load(fp)
    ID_list = file['data']['list']

    # 遍历所有收藏夹, 爬取所有收藏夹
    for i in ID_list:
        logger.info('爬取中...当前正在爬取{}'.format(i['title']))
        filename = os.path.join(WritePath, f"{i['title']}.json")

        # 获得一个收藏夹信息, 经过处理后一个json文件中
        data = GetOneFavorite(i['id'], math.ceil(i['media_count'] / 20) + 1)
        a_fav_data = CompareLastTime(filename, ProcessRawData(data))
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(a_fav_data, f, ensure_ascii=False)

    os.remove(os.path.join(id_path,'收藏夹id.json'))
    logger.info('所有收藏夹爬取完毕！！！')


def SetPhotoURl(ReadPath, uid):
    file_name_list = os.listdir(ReadPath)
    Cover_dict = {}
    Face_dict = {}
    for i in file_name_list:
        cover_url = {}  # 视频封面按收藏夹分类
        with open(os.path.join(ReadPath, i), 'r', encoding='utf-8') as f1:
            data = json.load(f1)
        for j in data.values():
            if j['是否失效']:
                cover_url['已失效视频'] = j['视频信息']['封面']
                logger.info('{}已失效'.format(j['视频信息']['标题']))
            else:
                cover_url[j['BV']] = j['视频信息']['封面']
            Face_dict[j['up主']['ID']] = j['up主']['头像']

        Cover_dict[i.split('.')[0]] = cover_url
    with open(os.path.join(uid, '视频封面url.json'), 'w', encoding='utf-8') as fp:
        json.dump(Cover_dict, fp, ensure_ascii=False)
    with open(os.path.join(uid, 'up头像url.json'), 'w', encoding='utf-8') as fp:
        json.dump(Face_dict, fp, ensure_ascii=False)


def download_picture(url):
    retry_count = 0
    while True:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # 检查内容是否是图片
                if response.headers.get('content-type', '').startswith('image/'):
                    return response.content
                else:
                    logger.warning(f"下载的内容不是图片: {url}")
            else:
                logger.warning(f"URL[{url}]下载错误[HTTP {response.status_code}]")
        except Exception as e:
            logger.warning(f"下载失败 (重试 {retry_count + 1}): {url}, 错误: {str(e)}")
            
        retry_count += 1
        time.sleep(1)  # 重试前等待1秒


# 爬取视频封面
def GetCover(Photo_path, PhotoURL_filename):
    count, MaxCount = 0, 0
    with open(PhotoURL_filename, 'r', encoding='utf-8') as fp:
        PhotoURL_dict = json.load(fp)
    for i in PhotoURL_dict.values():
        MaxCount += len(i.values())

    for fav_name in PhotoURL_dict.keys():
        # 视频封面按收藏夹分类
        Cover_Path = os.path.join(Photo_path, fav_name)
        if not os.path.exists(Cover_Path):
            os.makedirs(Cover_Path)
        
        url_list = []  # 放多个url进行多线程
        filepath_list = []  # 对应的文件路径列表
        fav_count = 0
        
        for BV, url in PhotoURL_dict[fav_name].items():
            count += 1
            fav_count += 1
            message = '[{}/{}]:视频封面{}{}[{}/{}]'.format(str(count), str(MaxCount), BV, fav_name, str(fav_count), str(len(PhotoURL_dict[fav_name])))
            logger.info(message)
            
            # 确定文件后缀名
            file_ext = os.path.splitext(url)[1].lower()
            if not file_ext or file_ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
                file_ext = '.jpg'  # 默认使用jpg格式
            
            filename = f'{BV}{file_ext}'
            filepath = os.path.join(Cover_Path, filename)
            
            # 如果文件已存在，跳过下载
            if os.path.exists(filepath):
                logger.info(f"文件已存在，跳过: {filename}")
                continue
                
            url_list.append(url)
            filepath_list.append(filepath)
            
            # 每10个URL或最后一组进行批量处理
            if len(url_list) == 10 or fav_count == len(PhotoURL_dict[fav_name]):
                # 定义工作函数，处理单个URL的下载
                def download_worker(url_filepath_pair):
                    url, filepath = url_filepath_pair
                    return download_picture(url), filepath
                
                # 准备任务列表
                tasks = list(zip(url_list, filepath_list))
                
                # 使用线程池并行下载
                with futures.ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_task = {executor.submit(download_worker, task): task for task in tasks}
                    
                    # 处理完成的任务
                    for future in futures.as_completed(future_to_task):
                        url, filepath = future_to_task[future]
                        try:
                            image_content, filepath = future.result()
                            if image_content:
                                with open(filepath, 'wb') as fp:
                                    fp.write(image_content)
                                logger.success(f"成功下载: {os.path.basename(filepath)}")
                        except Exception as e:
                            logger.error(f"下载或保存失败: {os.path.basename(filepath)}, 错误: {str(e)}")
                
                # 清空列表，准备下一批
                url_list.clear()
                filepath_list.clear()


def GetFace(Face_Path, PhotoURL_filename):
    with open(PhotoURL_filename, 'r', encoding='utf-8') as fp:
        PhotoURL_dict = json.load(fp)
    count, MaxCount = 0, len(PhotoURL_dict)

    if not os.path.exists(Face_Path):
        os.makedirs(Face_Path)

    url_list = []  # 放多个url进行多线程
    for ID, url in PhotoURL_dict.items():
        count += 1
        message = '[{}/{}]:up头像{}'.format(str(count), str(MaxCount), ID)
        
        # 确定文件后缀名
        file_ext = os.path.splitext(url)[1].lower()
        if not file_ext or file_ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
            file_ext = '.jpg'  # 默认使用jpg格式
        
        filename = f"{ID}{file_ext}"
        filepath = os.path.join(Face_Path, filename)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(filepath):
            logger.info(f"文件已存在，跳过: {filename}")
            continue
            
        if ID != "0":
            url_list.append((url, filepath, filename))
            logger.info(message)
        else:
            logger.debug(url)
            default_url = 'https://i0.hdslb.com/bfs/face/4ccdeb3afaaac140ed5aeb124aa053486a61a284.jpg'
            url_list.append((default_url, filepath, filename))
            logger.error('封面获取错误, 使用其他图片代替')
        
        # 每10个URL或最后一组进行批量处理
        if len(url_list) == 10 or count == MaxCount:
            def download_worker(item):
                url, filepath, filename = item
                image_content = download_picture(url)
                if image_content:
                    try:
                        # 处理webp格式转换
                        if url.lower().endswith('.webp') or filepath.lower().endswith('.webp'):
                            img = Image.open(io.BytesIO(image_content))
                            if img.mode in ('RGBA', 'LA'):
                                img = img.convert('RGB')
                            # 将webp转换为jpg
                            new_filepath = filepath.replace('.webp', '.jpg')
                            img.save(new_filepath, 'JPEG')
                            logger.success(f"成功下载并转换: {filename} -> {os.path.basename(new_filepath)}")
                        else:
                            with open(filepath, 'wb') as fp:
                                fp.write(image_content)
                    except Exception as e:
                        logger.error(f"保存文件失败: {filename}, 错误: {str(e)}")
                return filename
            
            # 使用线程池并行下载
            with futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_item = {executor.submit(download_worker, item): item for item in url_list}
                for future in futures.as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        logger.success(f"成功下载: {result}")
                    except Exception as e:
                        logger.error(f"下载线程异常: {item[2]}, 错误: {str(e)}")
            
            url_list = []  # 清空列表


def main(uid: str):
    logger.info(f'爬取用户{uid}')
    path1 = os.path.join(uid, '收藏夹信息')  # 存放信息的文件夹
    path2 = os.path.join(uid, '视频封面')  # 放视频封面的文件夹
    path3 = os.path.join(uid, 'up头像')  # 放up主头像的文件夹

    for i in (path1, path2, path3):
        if not os.path.exists(i):
            os.makedirs(i)

    time_list = []
    STime = time.perf_counter()
    GetFavoriteID(uid, uid) # 自己账号的uid
    GetALLFavorite(uid, path1)
    SetPhotoURl(path1, uid)
    while 1:
        try:
            GetCover(path2, os.path.join(uid, '视频封面url.json'))
            break
        except:
            logger.error('视频封面爬取异常, 重试中...')
            continue
    while 1:
        try:
            GetFace(path3, os.path.join(uid, 'up头像url.json'))
            break
        except:
            logger.error('up头像爬取异常, 重试中...')
            continue
    
    ETime = time.perf_counter()
    time_list.append(time.strftime("%M:%S", time.gmtime(ETime - STime)))
    STime = time.perf_counter()
    view(path1, os.path.join(uid, '收藏夹信息.xlsx'), path2, path3)
    ETime = time.perf_counter()
    time_list.append(time.strftime("%M:%S", time.gmtime(ETime - STime)))
    logger.info(f'执行爬取代码所用时间: {time_list[0]}')  # 视收藏视频数量和网速而定, 800视频大概五分钟
    logger.info(f'将数据写入excel文件所用时间: {time_list[1]}')  # 800视频大概两分半钟
    logger.success(f'用户{uid}爬取完成')

if __name__ == "__main__":
    now_time = datetime.now().strftime("%Y%m%d_%H-%M-%S")
    logger.add(os.path.join('log', f"{now_time}.log"), catch=True, retention='10 days')
    STime = time.perf_counter()
    uid_list = ['289920431'] # 账号的uid
    for i in uid_list:
        main(i)
    ETime = time.perf_counter()
    logger.info(f'总用时: {time.strftime("%H:%M:%S", time.gmtime(ETime - STime))}')
    logger.success('程序运行完成')
    
    input('程序运行完成, 按任意键以退出程序...')
    