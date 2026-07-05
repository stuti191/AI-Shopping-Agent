import os
import tempfile
# tempfile is used to create a temporary file for the uploaded image, which is then passed to the agent for analysis. The code handles both image uploads and text inputs, maintaining a chat history in the session state.

import streamlit as st

from shoppingAgent import agent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Shopping Assistant", page_icon="🛒", layout="wide")
# page_icon means that the page will have a shopping cart emoji as its icon in the browser tab. The layout is set to "wide" to utilize the full width of the page for better user experience.

st.title("🛒 AI Shopping Assistant")
st.caption("Tell me what you want — I'll search, rate, and order the best match for you.")
# small text below the title that explains the purpose of the app.

# ---------------------------------------------------------------------------
# Sidebar — shop by image
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Shop by Image")
    st.caption("Upload a photo of a product and I'll find similar items in our store.")

    uploaded_file = st.file_uploader(
        "Upload product image", type=["jpg", "jpeg", "png", "webp"]
    )
    # this creates an upload button in the sidebar that allows users to upload images of products. The accepted file types are jpg, jpeg, png, and webp.

    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)

    if uploaded_file and st.button("Find similar products", use_container_width=True):
    # this checks if a file has been uploaded and if the "Find similar products" button has been clicked. If both conditions are true, it processes the uploaded image.
        suffix = os.path.splitext(uploaded_file.name)[1] or ".jpg"
        # this line extracts the file extension from the uploaded file's name. If the file has no extension, it defaults to ".jpg". This is important for creating a temporary file with the correct format for further processing.
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            image_path = tmp.name
        # This block creates a temporary file with the same extension as the uploaded image. The image data is written to this temporary file, and its path is stored in `image_path`. This temporary file will be used for analysis by the agent. uploaded_file.getvalue() returns the binary content of the uploaded file, which is then written to the temporary file. The `delete=False` parameter ensures that the temporary file is not deleted when closed, allowing it to be accessed later for processing.

        prompt = f"I uploaded a product image. Please analyze it and find similar products in the store. Image path: {image_path}"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.pending_image = uploaded_file.name
        st.rerun()
        # st.session_state is a dictionary-like object that allows you to store information across reruns of the Streamlit app.Inside this, is a messages
        # list which is actually a list of dictionaries, where each dictionary represents a message in the chat. Each message has a "role" (either "user" or "assistant") and "content" (the text of the message). The prompt is added to this list as a new message from the user.Finally, `st.rerun()` is called to refresh the app and trigger the processing of the uploaded image by the agent.
        # there are 2 keys of session_state,one is messages which is a list of dictionary and another is pending_image which is a string that stores the name of the uploaded image file. The `pending_image` key is used to indicate that there is an image upload that needs to be processed by the agent. When the app reruns, it checks for this key to determine if it should invoke the agent to analyze the uploaded image and find similar products.
        # even after rerun,the session state is preserved, so the messages and pending_image remain accessible for further processing. 

# ---------------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render history — show a friendlier label for image-search messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user" and msg["content"].startswith("I uploaded a product image"):
            filename = msg["content"].split("Image path:")[-1].strip()
            st.markdown(f"Searching by image: **{os.path.basename(filename)}**")
        else:
            st.markdown(msg["content"].replace("$", r"\$"))
# For normal messages, the actual text is shown. For image-upload requests, instead of displaying the long internal prompt containing the temporary file path, it extracts the filename and shows a cleaner message like "Searching by image: filename.jpg".
# streamlit treats $ as a special character for LaTeX formatting, so to display it literally in the chat, it is escaped with a backslash. The `replace("$", r"\$")` ensures that any dollar signs in the message content are displayed correctly without triggering LaTeX rendering.
# ---------------------------------------------------------------------------
# Run agent if there's an unprocessed message (image upload triggers this)
# ---------------------------------------------------------------------------
if (
    st.session_state.messages
    and st.session_state.messages[-1]["role"] == "user"
    and "pending_image" in st.session_state
):
    with st.chat_message("assistant"):
        with st.spinner("Analyzing image and searching…"):
            result = agent.invoke({"messages": st.session_state.messages})
            response = result["messages"][-1].content.replace("`", "")
        st.markdown(response.replace("$", r"\$"))

    st.session_state.messages.append({"role": "assistant", "content": response})
    del st.session_state.pending_image
    # This line removes the `pending_image` key from the session state after the agent has processed the image and returned a response. This indicates that there is no longer an unprocessed image upload, preventing the agent from being invoked again for the same image.
    st.rerun()
    # it reruns the app to update the chat interface with the assistant's response and to clear the `pending_image` state, ensuring that the app is ready for new user inputs or image uploads.

# ---------------------------------------------------------------------------
# Text input
# ---------------------------------------------------------------------------
if prompt := st.chat_input("e.g. I want organic honey under $15 with 4+ rating"):
    # if prompt := st.chat_input(...): 
    # means  prompt = st.chat_input(...)
            # if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = agent.invoke({"messages": st.session_state.messages})
            response = result["messages"][-1].content.replace("`", "")
        st.markdown(response.replace("$", r"\$"))

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
