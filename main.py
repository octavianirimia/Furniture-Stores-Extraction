import csv
import json
import os
import spacy
import re
import spacy.tokens
import tabulate

from extract_website_data import extract_website_data



def load_text_file(file_path: str) -> set[str]:
    try:
        with open(file = file_path, mode = 'r', newline = '') as file:
            return set(file.read().splitlines())
        
    except FileNotFoundError:
        print(f"\nERROR: File not found: {file_path}\n")
        exit(1)



def load_currency_codes(file_path: str) -> set[str]:
    currencies: set[str] = set()

    try:
        with open(file = file_path, mode = 'r', newline = '') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row

            for row in reader:
                if len(row) >= 3 and row[2]:
                    currencies.add(row[2].lower())
                else:
                    print(f"Skipping row with insufficient columns: {row}")
    
    except FileNotFoundError:
        print(f"\nERROR: File not found: {file_path}\n")
        exit(1)

    return currencies



def extract_urls_from_csv(file_path: str) -> list:

    urls: list = []

    try:
        with open(file = file_path, mode = 'r', newline = '') as file:
            csvreader = csv.reader(file)
            next(csvreader, None) # Skipping first row

            for row in csvreader:
                if row:
                    urls.append(row[0].strip())

    except FileNotFoundError:
        print(f"\nERROR: CSV file not found: {file_path}\n")
        exit(1)

    return urls



def annotate_data(data: dict, annotation_rules: set[str], output_data_path: str, label: str):

    training_data: list = []
    nlp = spacy.blank('en')
    db = spacy.tokens.DocBin()
    
    # Annotate data
    for link, text in data.items():
        annotations: list[tuple] = []

        for rule in annotation_rules:
            pattern = re.compile(r"\b{}\b".format(re.escape(rule)), flags=re.IGNORECASE)
            matches = pattern.finditer(text)

            for x in matches:
                start, end = x.span()
                annotations.append((start, end, label))
            
        if annotations:
            training_data.append([link, text, {"entities": annotations}])

            doc = nlp(text)
            ents = []

            for start, end, _ in annotations:
                span = doc.char_span(start, end, label=label)
                ents.append(span)

            doc.ents = spacy.util.filter_spans(ents)
            db.add(doc)
    
    with open(f'{output_data_path}.json', 'w', encoding = 'utf-8') as file:
        json.dump(training_data, file, indent = 4)
    
    # Save training data spacy format to disk
    db.to_disk(f'{output_data_path}.spacy')



def test_model(model: str, data: dict) -> None:
    
    output_data: list = []
    furniture: dict = {}
    
    nlp = spacy.load(name = model)

    for link, line in data.items():
        doc = nlp(text = line)
        ents: list = []
        found_furniture: set = set()
        print(link, end = ": ")

        for ent in doc.ents:
            ents.append((ent.start_char, ent.end_char, ent.text, ent.label_))
            found_furniture.add(ent.text)

        if ents:
            output_data.append([link, line, {"entities": ents}])
            for item in found_furniture:
                if item in furniture:
                    furniture[item] = furniture[item] + 1
                else:
                    furniture[item] = 1
                print(item, end = ' ')
        print()

    # Save training data json format to disk
    with open('./assets/output_data.json', 'w', encoding = 'utf-8') as file:
        json.dump(output_data, file, indent = 4)

    furniture_type: str
    occurences: int = 0

    furniture = dict(sorted(furniture.items(), key = lambda x: x[1], reverse = True))

    data = [['Furniture', 'Number of occurrences']]
    for key in furniture:
        data.append([key, furniture[key]])

        if furniture[key] > occurences:
            occurences = furniture[key]
            furniture_type = key
    

    
    print(f"\n{furniture_type} has the maximum number of occurrences which is {occurences}\n".upper())
    
    table = tabulate.tabulate(data, tablefmt="grid")
    print(table)



def display_menu() -> None:
    print("\n1. Create training and evaluation data")
    print("2. Train the model")
    print("3. Test the model")
    print("4. Test for a single url")
    print("5. Exit")



def get_valid_choice() -> int:
    while True:
        choice = input("\nEnter your choice (1 - 5): ")
        try:
            choice = int(choice)
            if choice in range(1, 6):
                if choice == 5:
                    print("\nExiting the program ...\n")
                    exit(0)
                return choice
            else:
                print("\nYou should insert options from 1 to 4.")
        except ValueError:
            print("\nInvalid input. Please enter a number.")



def main() -> None:

    display_menu()
    choice: int = get_valid_choice()

    if choice == 1 or choice == 3 or choice == 4:
        # Load stop words
        stop_words_file: str = './assets/stop_words_english.txt'
        stop_words: set[str] = load_text_file(file_path = stop_words_file)
        print()
    
        # Load currency codes
        currency_codes_file: str = './assets/codes-all.csv'
        currency_codes: set[str] = load_currency_codes(file_path = currency_codes_file)
        currency_codes.add('lei')  # Adding 'LEI' to the currency set manually
        print()

        # Load furniture names
        furniture_names_file: str = './assets/furniture_names.txt'
        furniture_names: set[str] = load_text_file(file_path = furniture_names_file)
        print()

        # Extract urls from csv file
        urls_file = './assets/furniture_stores_pages.csv'
        urls: list = extract_urls_from_csv(file_path = urls_file)


    if choice == 1:
        # Extract data from first 100 websites for training
        website_training_data_output_path = './assets/website_training_data.txt'
        training_data: dict = extract_website_data(
            urls = urls[:100],
            stop_words = stop_words,
            currency_codes = currency_codes,
            file_path = website_training_data_output_path
        )

        # Training data annotation
        training_data_output_path = './assets/training_data'
        annotate_data(
            data = training_data,
            annotation_rules = furniture_names,
            output_data_path = training_data_output_path,
            label = 'FURNITURE'
        )

        # Extract data from first 50 websites for evaluation
        website_evaluation_data_output_path = './assets/website_evaluation_data.txt'
        evaluation_data: dict = extract_website_data(
            urls = urls[101:150],
            stop_words = stop_words,
            currency_codes = currency_codes,
            file_path = website_evaluation_data_output_path
        )

        # Evaluation data annotation
        evaluation_data_output_path = './assets/evaluation_data'
        annotate_data(
            data = evaluation_data,
            annotation_rules = furniture_names,
            output_data_path = evaluation_data_output_path,
            label = 'FURNITURE'
        )
    

    elif choice == 2:
        configuration_file_path: str = './assets/config.cfg'
        training_data_file_path: str = './assets/training_data.spacy'
        evaluation_data_file_path: str = './assets/evaluation_data.spacy'

        files: list[str] = [configuration_file_path, training_data_file_path, evaluation_data_file_path]

        files_exist: bool = all(map(os.path.isfile, files))

        if files_exist:
            os.system(f'python3.12 -m spacy train ./assets/config.cfg --output ./assets/output --paths.train ./assets/training_data.spacy --paths.dev ./assets/evaluation_data.spacy')


    elif choice == 3:
        # Extract data for testing
        website_testing_data_output_path = './assets/website_testing_data.txt'
        testing_data: dict = extract_website_data(
            urls = urls[151:],
            stop_words = stop_words,
            currency_codes = currency_codes,
            file_path = website_testing_data_output_path
        )

        model_file_path: str = './assets/output/model-best'

        test_model(model = model_file_path, data = testing_data)
    

    else:
        url: str = input("Insert URL: ")
        data: dict = extract_website_data(
            urls = [url],
            stop_words = stop_words,
            currency_codes = currency_codes
        )

        model_file_path: str = './assets/output/model-best'

        if not data:
            print("\nData could not be retrieved!\n")
            exit(1)

        test_model(model = model_file_path, data = data)



if __name__ == '__main__':
    main()