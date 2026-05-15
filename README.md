# Project Overview

This project contains Python scripts and shell utilities for automation.

## Structure
- /datadisk/daily/gm/audio/aac/: place to move video that have aac and opus audio to it
- /datadisk/daily/gm/audio/eac3/: place to move video that have eac3 audio to it
- /datadisk/daily/gm/: place that use to run extracksub.py -c ,-n  and other depend on video file you can read inside it 
-/diskdata/winbackup/Desktop/mpd/pythonsubtools/numgen.py : a file that use to generate file name if it not exist on [bilili](https://www.bilibili.tv/th/timeline)
-/diskdata/winbackup/Desktop/mpd/pythonsubtools/numbers.json : a json file that contains name that output from "/diskdata/winbackup/Desktop/mpd/pythonsubtools/numgen.py" 
- /datadisk/daily/vidori.sh :  run to encode 720p video turn any mkv to av1 720p
- /datadisk/daily/1080/1080T2/vidori1080p8crf30.sh:  run to encode 1080p video turn any mkv to av1 1080p at preset 8 crf 30
- /datadisk/daily/cn/cnvid.sh : this is for chinese animation that is mostly 1920x816
- /datadisk/daily/1080/auto-boost_2.5_1080.py : to encode 1080p video to av1 with more care
- /datadisk/daily/extau.py : file that run to extract audio it use by run it with -a for aac -o for opus -e for eac3

## Usage
Describe how to run stuff here
after download video to  /datadisk/daily/ or /datadisk/daily/1080 or /datadisk/daily/1080/1080T2 or /datadisk/daily/cn
it will run  ./vidori.sh if it on  /datadisk/daily/   if  /datadisk/daily/1080  it will run auto-boost_2.5_1080.py  -i file.mkv -gpu 
if it success remove folder that name is start with . in /datadisk/daily/1080 then run vidori1080p4crf30r3.sh  
if  it on /datadisk/daily/1080/1080T2 run  vidori1080p8crf30.sh  
if /datadisk/daily/cn run ./cnvid.sh
then all of it it will output videofilename_mux.mkv it will copy *_mux.mkv into /datadisk/daily/gm 
then check which one is exist on https://www.bilibili.tv/th/timeline   it will run /usr/bin/python3 /diskdata/winbackup/Desktop/mpd/bilibilidownloader/app.py
it will place url one link per line  that relied to /diskdata/winbackup/Desktop/mpd/bilibilidownloader/templates/index.html  
    <h1>Sub only but all sub</h1>
    <form action="/biliSubs" method="post">
        <label for="bilibili_urls">Enter Bilibili URLs without id:</label>
        <textarea id="bilibili_Subs" name="bilibili_Subs" rows="4" cols="50"></textarea><br><br>
        <input type="submit" value="Download Subtitle">
    </form>
    then submit form then output will go out to  /diskdata/winbackup/Desktop/mpd/bilibilidownloader/animeBiliBili/
    i will have multiple folder the way you know is check recent time that just download and copy lasted episode subtitle to datadisk/daily/gm 
    then change name of mkv file if it have same name  like  I.Want.You.To.Show.Me.Your.Panties.With.a.Disgusted.Face.Returns.S01E01.1080p.AMZN.WEB-DL.JPN.DDP2.0.H.264.MSubs-ToonsHub.mkv and I.Want.You.To.Show.Me.Your.Panties.With.a.Disgusted.Face.Returns.S01E01.1080p.AMZN.WEB-DL.JPN.DDP2.0.H.264.MSubs-ToonsHub_mux.mkv  
    and subtitle from bilibili is I Want You To Show Me Your Panties With a Disgusted Face Returns_EP01_30554569_0_tha_BiliBiliTH.srt
    so filename gonna change like I Want You To Show Me Your Panties With a Disgusted Face Returns_EP01_30554569_720p.mkv for I.Want.You.To.Show.Me.Your.Panties.With.a.Disgusted.Face.Returns.S01E01.1080p.AMZN.WEB-DL.JPN.DDP2.0.H.264.MSubs-ToonsHub_mux.mkv  
    if I.Want.You.To.Show.Me.Your.Panties.With.a.Disgusted.Face.Returns.S01E01.1080p.AMZN.WEB-DL.JPN.DDP2.0.H.264.MSubs-ToonsHub.mkv  change to I Want You To Show Me Your Panties With a Disgusted Face Returns_EP01_30554569.mkv
    and if it doesn't have subtitle from bilibili like Haibaras.Teenage.New.Game.S01E05.Ill.Give.You.an.Umbrella.When.Youre.In.the.Rain.1080p.CR.WEB-DL.AAC2.0.H.264-VARYG.mkv it is gonna cd to
    /datadisk/uckl/unshackle and run uv run unshackle -d dl -al ja-jp -w S01E05 (use value from file name i.e. S01E05) -S RC "https://www.crunchyroll.com/series/GT00371668/haibaras-teenage-new-game"
    url link contains in /datadisk/daily/gm/animelink.txt it have one link per line output will go to  /datadisk/unshackle/unshackle/downloads/   it will give xxxfilename.mks i.e haibaras is 
    in Haibaras.Teenage.New.Game+.S01.RC.WEB-DL folder i want you to check recent file that download and on /datadisk/unshackle/unshackle/downloads/ and copy .mks to /datadisk/daily/gm
    and after that cd to "/diskdata/winbackup/Desktop/mpd/pythonsubtools/"  and run py numgen.py  before that search anilist api using this graphql to https://graphql.anilist.co
    query ($season: MediaSeason, $seasonYear: Int,$page: Int,$search: String!) { 
  Page(page: $page, perPage: 50) {
    pageInfo {
      currentPage
      hasNextPage
    }
    media(
      season: $season
      seasonYear: $seasonYear
      type: ANIME
      search: $search 
    ) {
      id
      season
      seasonYear
      title {
        romaji
        english
        native
      }
      coverImage {
        extraLarge
      }
      startDate {
        year
        month
        day
      }
    }
  }
}
and search by using filename like 
{

  "search": "Haibaras.Teenage.New.Game"

}
it will response like this 
{
  "data": {
    "Page": {
      "pageInfo": {
        "currentPage": 1,
        "hasNextPage": false
      },
      "media": [
        {
          "id": 195333,
          "season": "SPRING",
          "seasonYear": 2026,
          "title": {
            "romaji": "Haibara-kun no Tsuyokute Seishun New Game",
            "english": "Haibara's Teenage New Game+",
            "native": "灰原くんの強くて青春ニューゲーム"
          },
          "coverImage": {
            "extraLarge": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx195333-KUIF1eqOdVdd.png"
          },
          "startDate": {
            "year": 2026,
            "month": 4,
            "day": 3
          }
        }
      ]
    }
  }
}
and target on romaji which is Haibara-kun no Tsuyokute Seishun New Game"   then run numgen.py Haibara-kun no Tsuyokute Seishun New Game_EP05  and enter 
then it will save name to clipboard and rename  Haibaras.Teenage.New.Game.S01E05.Ill.Give.You.an.Umbrella.When.Youre.In.the.Rain.1080p.CR.WEB-DL.AAC2.0.H.264-VARYG.mkv
to Haibara-kun no Tsuyokute Seishun New Game_EP05_89568211.mkv and Haibaras.Teenage.New.Game.S01E05.Ill.Give.You.an.Umbrella.When.Youre.In.the.Rain.1080p.CR.WEB-DL.AAC2.0.H.264-VARYG_mux.mkv to "Haibara-kun no Tsuyokute Seishun New Game_EP05_89568211_720p.mkv"
then for the mks that we've got from unshackle that on /datadisk/unshackle/unshackle/downloads/  and check recent file anding to this folder and subfolder "/datadisk/unshackle/unshackle/downloads/Haibaras.Teenage.New.Game+.S01.RC.WEB-DL" it will found Haibaras.Teenage.New.Game+.S01E05.Ill.Give.You.an.Umbrella.When.Youre.In.the.Rain.RC.WEB-DL.mks  change it to Haibara-kun no Tsuyokute Seishun New Game_EP05_89568211.mkv then call py extracksub -c if we run it from RC it mean we need to Haibara-kun no Tsuyokute Seishun New Game_EP05_89568211.mkv then call py extracksub.py -c enter and paste Haibara-kun no Tsuyokute Seishun New Game_EP05_89568211.mkv  then move all srt and  ass to datadisk/daily/gm   repeat this process to all mkv file with dif name then run assheaderedit.py to edit all ass subtitle  then run udmv4linux.py  after finish run _supnamerm.py then run oldrm.py# mediamng
