# 3D Audio Simulator

This is my final project for CS 448: 3D Audio Simulator. My system enables users to:

- Position themselves in a virtual 2D plane
- Place multiple audio sources around their position
- Define paths for these audio sources to move along
- Upload / select audio files for each source
- Simulate how these audio movements would sound from their position

A video demo is available [here](https://www.youtube.com/watch?v=Ph8rozVB65s). 

To run the system, clone the repository and run `python3 app.py`. Make sure you have all dependencies in `app.py` installed. Then, navigate to `http://127.0.0.1:5000/` in your web browser and simulate!

## Some notes:

- In order to define a path for an entity / audio source, check the box "Define Path For This Entity" **before** you place the first position of the source
- When you are done defining a path for an entity, uncheck this box (and then re-check it as needed)
