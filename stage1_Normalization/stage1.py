import os
from cv2 import imread,imwrite
from pypdf import PdfReader

path   = ""
SUPPORTED_EXTENSIONS = ["jpg", "jpeg", "png", "pdf"]

# All working files go here — original is preserved
working_directory = "local datastore"

def detect_pdf_type(pdf_path):
    #We read the first page and try to extract text.
    #- If meaningful text is found → vector PDF

    reader = PdfReader(pdf_path)

    # Check first page for extractable text
    first_page = reader.pages[0]
    text = first_page.extract_text() or ""

    # Clean up whitespace and check if real text exists
    clean_text = text.strip().replace("\n", "").replace(" ", "")
    
    if len(clean_text) > 20:
        return "vector"
    else:
        return "image_based"


def handle_image(file_path):
    #Returns : path to the normalized PNG

    image = imread(file_path)
    if image is None:
        raise ValueError("Could not read image file: " + file_path)

    # save to working directory
    output_path = working_directory+"\\"+"main.png"
    print(output_path)
    imwrite(output_path, image)
    return output_path


def handle_image_based_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        page = reader.pages[0]
        images = list(page.images)

        # strict expectations: exactly 1 image
        if len(images) != 1:
            raise Exception()

        img = images[0]

        # allow only jpg/png
        name = img.name.lower()
        if name.endswith((".jpg", ".jpeg")):
            ext = "jpg"
        elif name.endswith(".png"):
            ext = "png"
        else:
            raise Exception()

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(working_directory, f"{base_name}_page1.{ext}")

        with open(output_path, "wb") as f:
            f.write(img.data)

        return output_path

    except Exception:
        raise ValueError("Invalid PDF")


def handle_vector_pdf(file_path):
    output_path = working_directory+"\\"+"main.pdf"

    source=open(file_path, "rb") 
    destination=open(output_path, "wb")
    
    destination.write(source.read())

    return output_path



#first run function
def run_input_normalization(file_path):
    """
    Args:
        file_path : path to the input file (JPG, JPEG, PNG, or PDF)

    Returns:"file_type"     : "image" | "image_based_pdf" | "vector_pdf"
            "status"        : "ok" or "error"
    
    """

    #Creates the working directory if it does not exist.
    os.makedirs(working_directory, exist_ok=True)

    print("\n[Stage 1] Input Normalization")
    print("Input : ", file_path)
    

    # check path
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError("File not found: ",file_path)

        input_extension = str(file_path).split('.')[-1].lower()
        # print("CHECK :: ",input_extension)
        
        if input_extension not in SUPPORTED_EXTENSIONS:
            raise ValueError( "Unsupported Format: ",input_extension,"\n","Accepted formats: JPG, JPEG, PNG, PDF")
        else:
            print("\nFormat Supported : ", input_extension.upper(),"\n")

    except (FileNotFoundError, ValueError) as e:
        print(f"  ERROR: {e}")
        return {
            "file_type"  : None,
            "status"  : "error",
            "message" : e

        }

    #ext = os.path.splitext(file_path)[1].lower()

    #CASE 1: Image file 
    if input_extension in ["jpg", "jpeg", "png"]:
        output_path = handle_image(file_path)
        file_type   = "image"
        next_stage = 2

    #CASE 2: PDF file 
    elif input_extension == "pdf":
        pdf_type = detect_pdf_type(file_path)

        if pdf_type == "image_based":
            output_path = handle_image_based_pdf(file_path)
            next_stage = 2
            file_type   = "image_based_pdf"
        else:
            output_path = handle_vector_pdf(file_path)
            file_type   = "vector_pdf"
            next_stage = 4
        

    else:
        file_type=None
    
    
    return {
        "input_path" :  file_path,
        "output_path": output_path,
        "next_stage" : next_stage,
        "file_type"  : file_type,
        "status"     : "ok"
    }


if __name__ == "__main__":
    
    # image_name =
    
    result = run_input_normalization(path)

    if result["status"] == "ok":
        print("Output file Generated")
        print("File type : ", result["file_type"])
    else:
        print("Error")
