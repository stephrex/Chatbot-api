class GetData():
    def __init__(self, client_db):
        self.client_db = client_db

    def get_client_db(self):
        '''
        Get Client Db if client uses Firebase firestore to store product data
        This function should change depending on the client firebase data storage format
        '''
        db_ref = self.client_db.collection("books")
        docs = db_ref.stream()

        books = []
        for doc in docs:
            books.append(doc.to_dict())

        return books

    def run(self):
        return self.get_client_db()
