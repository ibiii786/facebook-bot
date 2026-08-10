def on_key(event,canvas):
    if event.keysym == "Down":
        canvas.yview_moveto(canvas.yview()[0]+0.1)  # Move all the way to the bottom
    elif event.keysym == "Up":
        canvas.yview_moveto(canvas.yview()[0]-0.1) 
def on_scroll(event, canvas):
    if event.delta:
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")