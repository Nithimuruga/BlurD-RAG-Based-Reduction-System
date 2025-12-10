from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DETAILS = "mongodb://localhost:27017"
client = None

def get_database():
    return client["test_db"] if client else None

async def connect_to_mongo():
    global client
    try:
        client = AsyncIOMotorClient(MONGO_DETAILS)
        # Test the connection
        await client.admin.command('ping')
        print("Connected to MongoDB successfully")
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        print("API will start but database operations will fail")
        client = None

async def close_mongo_connection():
    global client
    if client:
        client.close()
