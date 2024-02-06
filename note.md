東京大学技術経営戦略学専攻の進路（データサイエンスの覇権である松尾研究室の進路の代替として）
https://tmi.t.u-tokyo.ac.jp/gratuates

# install
conda install requests beautifulsoup4

# フォントの設定
plt.rcParams['font.family'] = 'Meiryo'  # 使用するフォント名を指定


検索欄の例
https://en-hyouban.com/
<input type="text" class="col-md-10 col-12 home_search_input" placeholder="企業名・キーワードで検索" id="home_search_text" name="SearchWords" maxlength="50">
/html/body/main/div[1]/div[1]/div[1]/div[1]/div[2]/div/form/div/input[1]

企業ページの例
https://en-hyouban.com/company/00168958828/
企業名
/html/body/main/div[1]/div[1]/div/div[1]/h1
<h1 class="typography-hy-1 float-left pr-lg-0 pr-md-0 pr-3">ゴールドマン・サックス証券株式会社<span class="typography-hy-2">の評判・口コミ</span></h1>
年収
<span class="fsize-40 font-change-30 font-roboto font-weight-bold">1497</span>
/html/body/main/div[1]/div[1]/div/div[2]/div[5]/div[3]/div/div/div[1]/div/div[2]/span[1]
残業
<span class="fsize-40 font-change-30 font-roboto font-weight-bold">66</span>
/html/body/main/div[1]/div[1]/div/div[2]/div[5]/div[3]/div/div/div[2]/div[2]/span[1]


企業ページの詳細ページA
https://en-hyouban.com/company/00009367890/salary/
00009367890 is company ID example


25-29歳の平均年収
<span class="font-roboto color-link salary-font-size">782</span>
/html/body/main/div[4]/div[1]/div/div/div[1]/div[2]/div/table/tbody/tr[1]/td[2]/span[1]

30-34歳の平均年収
<span class="font-roboto color-link salary-font-size">1229</span>
/html/body/main/div[4]/div[1]/div/div/div[1]/div[2]/div/table/tbody/tr[2]/td[2]/span[1]