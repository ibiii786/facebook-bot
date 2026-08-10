import pandas as pd
CSV_FILE = "saved_states.csv"
def make_files(entries,emails,location="",market_location="UK"):
        try:
                df=pd.read_csv(CSV_FILE)
                title = entries[1].get()
                price = entries[6].get()
                category = entries[3].get()
                condition = entries[7].get()
                description = entries[2].get("1.0", "end").strip()
                availability = entries[8].get()
                product_tags = [tag for tag in entries[5].get().split(",")]
                images = [img.get() for img in entries[0]]
                video = entries[9].get().strip()

                opt_vars = entries[11]
                

                unique_name = title + '||||' + str(emails)
                new_row = pd.DataFrame([
                    {
                        'Name': unique_name,
                        'Title': title,
                        'Price': price,
                        'Category': category,
                        'Condition': condition,
                        'Description': description,
                        'Availability': availability,
                        'Product_Tags': product_tags,
                        'Images': images,
                        'Video': video,
                        'public_meetup': opt_vars[0].get(),
                        'door_dropoff': opt_vars[1].get(),
                        'door_meetup': opt_vars[2].get(),
                        'Location': location,
                        'Status': False,
                        'Market_Location': market_location
                    }
                ])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
        except Exception:
                import traceback
                traceback.print_exc()
def set_file_status(title,emails):
        df=pd.read_csv(CSV_FILE)
        unique_name=title+'||||'+str(emails)
        df.loc[df['Name'] == unique_name, 'Status'] = True
        df.to_csv(CSV_FILE, index=False)