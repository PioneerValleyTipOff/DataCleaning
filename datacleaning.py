#make sure these are installed:
#urllib, html-table-parser-python3, xlsxwriter, openpyxl
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
import urllib.request #gets access to turbostats
from html_table_parser.parser import HTMLTableParser #extract table data from turbostats
import pandas as pd #helps clean the data
import numpy as np #used to flip for opposing team stats as necessary
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#opens a site and read HTTP for turbostats
def url_get_contents(link):
    #making request to the website to access data
    request_link = urllib.request.Request(url=link)
    content = urllib.request.urlopen(request_link)

    #reading contents from the website
    return content.read()
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def dataset(game: str):
  site = 'https://www.turbostatsevents.com/site/2/boxscore/basketball/pioneervalleytipoff/'

  #modify the year variable for when the event is taking place
  year = '2022'

  #defining the HTMLTableParser class object and feed the html parser from the function above. 
  #using this, we are able to use the .tables feature to extract the tables from Turbostats
  retrive = HTMLTableParser()

  #using .decode() here helps convert the html contents into useable data
  retrive.feed(url_get_contents(site+year+'/'+game).decode('utf-8'))

  #the two teams from each game. on turbostats, team1 is the team you see first
  #on boxscore and team2 is 2nd team on boxscore
  team1 = retrive.tables[0][1][0]
  team2 = retrive.tables[0][2][0]
  teams = [team1, team2]
  
  game_data = []

  #extract data from each team
  for j in range(len(teams)):
    players_df = pd.DataFrame(retrive.tables[j+1])
    players_df.rename(columns=players_df.iloc[0], inplace = True)
    players_df.drop(0,axis=0,inplace = True)
    players_df.insert(0,'Team',teams[j])
    players_df.drop('Net', axis=1, inplace=True) 
    game_data.append(players_df)   

  #took each of the teams from each game and combined them together
  game_data = pd.concat(game_data, axis=0)

  #we will separate out the player and team totals to have two datasets, which
  #are player and team datasets. this will help as we can analyze on a holisitc
  #level from each team and on a micro level, which is the players data.

  #this is the team results from each game
  game_results = game_data[game_data["Name"] == "Totals"]
  game_results = game_results.reset_index(drop=True)
  game_results.loc[0,'Name'] = teams[0]
  game_results.loc[1,'Name'] = teams[1]
  #dropping +- since it's not that useful in a team context
  game_results.drop(['Number', 'Team', '+-'], axis=1, inplace=True)

  #this is the players stats from each game
  game_data = game_data[(game_data["Name"] != "Totals") & (game_data["Name"] != "TEAM")]
  game_data = game_data.reset_index(drop=True)

  #converting to numeric data to let us add other stats for player and team data
  #we can see that player info is separated from team info in this case as well 
  player_info = game_data.iloc[:,0:3]
  player_stats = game_data.iloc[:,3:].apply(pd.to_numeric)

  team_info = game_results.iloc[:,0]
  team_stats = game_results.iloc[:,1:].apply(pd.to_numeric)

  game_data = pd.concat([player_info, player_stats], axis=1).reset_index(drop=True)
  game_results = pd.concat([team_info, team_stats], axis=1).reset_index(drop=True)

  #modify the datasets and add specific columns that were not from turbostats
  game_data.insert(10,'Efg%', round(((game_data['Fgm'] + 0.5*game_data['3fgm']) / game_data['Fga']),3))
  game_data.insert(11,'Ts%', round(game_data['Points'] / (2 * (game_data['Fga'] + (.475*game_data['Fta']))),3))
  game_data.insert(22,'To%', round((game_data['To'] / (game_data['Fga'] + .475*game_data['Fta'] + game_data['To'])),3))

  #every other column inserted is opponet stats. this will be useful as these 
  #are from Dean Oliver's 4 Factors
  game_results.insert(8,'Efg%', round(((game_results['Fgm'] + 0.5*game_results['3fgm']) / game_results['Fga']),3))
  game_results.insert(9,'Opp_Efg%', list(np.flip(game_results['Efg%'])))
  game_results.insert(10,'Ts%', round(game_results['Points'] / (2 * (game_results['Fga'] + (.475*game_results['Fta']))),3))
  game_results.insert(11, 'Ft/Fga', round((game_results['Fta']/game_results['Fga']),3))
  game_results.insert(12, 'Opp_Ft/Fga', list(np.flip(game_results['Ft/Fga'])))
  game_results.insert(17,'RebO%', round((game_results['RebO']/(game_results['RebO']+list(np.flip(game_results['RebD'])))),3))
  game_results.insert(18,'RebD%', round((game_results['RebD']/(game_results['RebD']+list(np.flip(game_results['RebO'])))),3))
  game_results.insert(19,'To%', round((game_results['To'] / (game_results['Fga'] + .475*game_results['Fta'] + game_results['To'])),3))
  game_results.insert(20,'Opp_To%', list(np.flip(game_results['To%'])))

  return [game_data, game_results]
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#this is separate so that you can test whether data matches desired format
def all_datasets():
  #team and player data arrays
  player_data = []
  team_data = []

  #total amount of games, change as needed
  games = 11

  #start from 1 instead of 0 since the games from turbostats start with 1 
  for i in range(1,games):
    #if any specifc game is canceled or missing data, use guard if statement
    #to do this, look in site link and see game number at the very end
    if i == 4:
      continue
    player, team = dataset(str(i))
    player_data.append(player)
    team_data.append(team)

  #gathers all of the data at the end
  player_data = pd.concat(player_data, axis=0).reset_index(drop=True)
  team_data = pd.concat(team_data, axis=0).reset_index(drop=True)

  return [player_data, team_data]
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#put desired path that you have into here
def write_to_excel(path = input()):
  combined_player, combined_team = all_datasets()

  #creates excel workbook containing all of the PVTO data
  writer = pd.ExcelWriter(path + '/PVTOData.xlsx', engine='xlsxwriter')
  writer.save()

  #puts each of the player and team data into separate sheets
  with pd.ExcelWriter(path + '/PVTOData.xlsx', engine='openpyxl', mode='a') as writer:
      combined_player.to_excel(writer, sheet_name='PlayerData', index=False)
      combined_team.to_excel(writer, sheet_name='TeamData', index=False)
  
  return 'Player and team data uploaded.'

#for future use, copy your own computer path and paste it 
#so that the excel workbook will go straight there
write_to_excel()
