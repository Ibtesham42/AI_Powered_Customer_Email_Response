from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = []
    seen_chunks = set()

    for doc in documents:

        split_text = splitter.split_text(doc["text"])

        for chunk in split_text:

            clean_chunk = chunk.strip()

            # duplicate check
            if clean_chunk not in seen_chunks:

                chunks.append({
                    "text": clean_chunk,
                    "metadata": doc["metadata"]
                })

                seen_chunks.add(clean_chunk)

    print("Total unique chunks:", len(chunks))

    return chunks