#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 21 17:07:46 2017

@author: JacobLandau
"""

import tkinter, tkinter.messagebox, tkinter.filedialog #GUI library
import PIL.Image, PIL.ImageTk #Image library
import tmdbsimple as tmdb #The Movie DB API wrapper; some calls are made directly as this wrapper is poorly documented
from pytube import YouTube #YouTube stream browser and downloader
import requests, re, io, os, random, sys

tmdb.API_KEY = '[INSERT_v3_KEY_HERE]' 

class PreshowGenerator(tkinter.Frame):
    
    def __init__(self, master):
        #initializes tkinter Frame and initializes the film's id number and the file path
        self.master = master
        tkinter.Frame.__init__(self, master)
        self.id = 0
        self.file_path = ''
        
        #button to trigger function to select and open a file
        self.file_select_button = tkinter.Button(master, text='Open File',command=self.file_select)
        self.file_select_button.grid(row=2,column=1,columnspan=2,sticky='we')
        
        #Label and field for entry of film title
        self.title_prompt = tkinter.Label(master, justify='left',text='Title: ')
        self.title_prompt.grid(row=0,column=0)
        self.title_field = tkinter.Entry(master)
        self.title_field.grid(row=0,column=1,columnspan=2,sticky='we')
        
        #button to trigger verification function
        self.verified = False
        self.verify_button = tkinter.Button(master, text='Verify', command=self.verify)
        self.verify_button.grid(row=1,column=0,columnspan=3,sticky='we')
        
        #sets the PIL image object to the default and halves the scale
        #image will be changed as verified films have posters pulled from IMDB
        self.poster_image = PIL.Image.open('default.jpg')
        self.poster_image = self.poster_image.resize((self.poster_image.size[0]//2,self.poster_image.size[1]//2), PIL.Image.ANTIALIAS)
        #creates Tk-compatible photoimage from poster_image, and places it into label
        self.poster = PIL.ImageTk.PhotoImage(self.poster_image)
        self.poster_label = tkinter.Label(master, image=self.poster, borderwidth=0)
        self.poster_label.grid(row=0,column=3,rowspan=5)
        
        #sets the number of trailers
        self.trailers = tkinter.IntVar()
        self.trailers.set(3)
        self.trailer_prompt = tkinter.Label(master, justify='center',text='# of Trailers: ')
        self.trailer_prompt.grid(row=3,column=0)
        self.trailer_field = tkinter.OptionMenu(master, self.trailers, *range(1,6))
        self.trailer_field.grid(row=3,column=1)
        
        #sets age restriction, IntVar is required for tkinter Checkbutton, but
        #in Python 1 == True & 0 == False. Slightly disgusting, but it works
        self.age = tkinter.IntVar()
        self.age.set(1)
        self.age_button = tkinter.Checkbutton(master, text='Include mature films?',variable=self.age)
        self.age_button.grid(row=4,column=0)
        
        #sets policy trailer option
        self.policy = tkinter.IntVar()
        self.policy.set(1)
        self.policy_button = tkinter.Checkbutton(master,text='Include policy trailers?',variable=self.policy)
        self.policy_button.grid(row=4,column=1)
        
        #button to generate playlist
        self.generate_button = tkinter.Button(master, text='Generate Playlist',command=self.generate_playlist)
        self.generate_button.grid(row=5,column=0,columnspan=2,sticky='we')
        
        
    
    def file_select(self):
        '''Grabs a preexisting log file and adds it to the working archive

        Attributes:
            file_path (str): path to the selected file
            file_select_text (:obj:`tkinter.Label`): label to display file name
        '''
        #opens a filedialog that asks for a video file with an acceptable container
        self.file_path = tkinter.filedialog.askopenfilename(filetypes=[('MP4/MKV/WMV/AVI','*.mp4;*.mkv;*.wmv;*.avi')])

        #creates label showing the file's name
        #regex pulls the name from the file path by matching the last f-slash
        file_select_text = tkinter.Label(self.master, justify='left', text=re.findall(r'.+/(.+)', self.file_path)[0])
        file_select_text.grid(row=2,column=0)
        
    def verify(self):
        '''Verifies with TMDB that the film exists

        Attributes:
            search.results[0] (dict): dictionary of attributes for the film to be verified
        '''
        search = tmdb.Search()
        response = search.movie(query=self.title_field.get())
        
        #checks if the search has yielded any results
        if len(search.results) > 0:
            #sets the id equal to that for our film
            self.id = search.results[0]['id']
            
            #configuration parameters for poster
            response = requests.get(f'https://api.themoviedb.org/3/configuration?api_key={tmdb.API_KEY}')
            image_prefix = response.json()['images']['secure_base_url']
            
            #grab movie poster url
            response = requests.get(f"https://api.themoviedb.org/3/movie/{self.id}/images?api_key={tmdb.API_KEY}")
            images = response.json()
            poster_url = image_prefix + 'original' + images['posters'][0]['file_path']
            
            #points poster_image to a new PIL Image opened from bytestream
            #obtained using a GET request
            self.poster_image = PIL.Image.open(io.BytesIO(requests.get(poster_url).content))
            self.poster_image = self.poster_image.resize((150,234), PIL.Image.ANTIALIAS)
            #points poster to new PhotoImage generated from new poster_image
            self.poster = PIL.ImageTk.PhotoImage(self.poster_image)
            #points poster_lable to new poster
            self.poster_label.configure(image=self.poster)
            
            #notifies user that the film exists as verified
            tkinter.messagebox.showinfo('Verification Status','This film exists!')
            self.verified = True
        else:
            #notifies user that the film does not exist
            tkinter.messagebox.showerror('Verification Status','That film does not exist')
            self.verified = False
    
    def generate_playlist(self):

        #if the film has been selected and the data confirmed
        if self.verified:
            
            #removes films from the prior playlist
            for item in os.listdir(os.getcwd()):
                if item.endswith('.mp4'):
                    os.remove(os.path.join(os.getcwd(),item))
            
            #grabs 20 most popular upcoming new films
            trailer_films = []
            upcoming_films = requests.get(f'https://api.themoviedb.org/3/movie/upcoming?api_key={tmdb.API_KEY}&language=en-US&page=1').json()
            #creates movie object from our feature's ID, collects all applicable genres for the feature
            movie = tmdb.Movies(self.id)
            response = movie.info()
            movie_genres = [i['id'] for i in movie.genres]
            
            for film in upcoming_films['results']:
                #sets the genre matches as the number of genres shared between the feature and the upcoming film
                genre_matches = len(set(movie_genres).intersection(film['genre_ids']))
                #if there are matches, and the film has a basic level of quality
                if genre_matches > 0 and film['popularity'] > 25:
                    #the id of the trailer candidate is added to the list
                    trailer_films.append((film['id'], genre_matches))
                else:
                    continue

            #trailer candidates are sorted by the number of matches, descending
            trailer_films.sort(key=lambda x: x[1])
            trailer_films = trailer_films[::-1]
            #the number of trailers is cut off to the maximum set by the user
            trailer_films = trailer_films[0:self.trailers.get()]
            #the trailers to be used are shuffled to keep things fresh
            random.shuffle(trailer_films)
            
            #for every accepted candidate, the link to the first trailer is downloaded
            for film in trailer_films:
                key = requests.get(f'https://api.themoviedb.org/3/movie/{film[0]}/videos?api_key={tmdb.API_KEY}&language=en-US').json()['results'][0]['key']
                YouTube(f'http://www.youtube.com/watch?v={key}').streams.first().download()
            
            
            #opens a filedialog prompting user to set file location and name
            file_path = tkinter.filedialog.asksaveasfilename(defaultextension='.m3u',filetypes=[('Extended M3U Playlist Format','*.m3u')])
            
            #writes content to playlist file
            with open(file_path,'w') as file:
                file.write('#EXTM3U\n') #file header
                if self.policy.get():
                    file.write('D:\jakel\\Documents\\GitHub\\PreshowGenerator\\trailers\\policy\\lobby.mp4\n')
                file.write('D:\\jakel\\Documents\\GitHub\\PreshowGenerator\\trailers\\policy\\comingsoon.mp4\n')
                
                #grabs all files in the working directory which are .mp4s (i.e. our trailers)
                files = [f for f in os.listdir('.') if os.path.isfile(f)]
                files = [f for f in files if f[-4:] == '.mp4']
                #writes all trailers to the M3U in order
                for f in files:
                    file.write(os.getcwd() + '\\' + f + '\n')
                if self.policy.get():
                    file.write('D:\\jakel\\Documents\\GitHub\\PreshowGenerator\\trailers\\policy\\tommytexter.mp4\n')
                file.write('D:\\jakel\\Documents\\GitHub\\PreshowGenerator\\trailers\\policy\\featurepresentation.mp4\n')
                #writes file path of feature to end of playlist
                file.write(self.file_path)
                tkinter.messagebox.showinfo('Playlist Created','The playlist has been created at the specified location!')
        else:
            tkinter.messagebox.showerror('Verification Error','This film has not been verified. Please verify your film to generate a preshow.')
    
if __name__ == '__main__':
    #configures and runs the tkinter backbone
    root = tkinter.Tk()
    root.title('Preshow Generator')
    root.wm_iconbitmap('icon.ico')
    app = PreshowGenerator(root)
    root.mainloop()