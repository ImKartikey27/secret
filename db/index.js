import mongoose from "mongoose";

const connectDB = async () => {
    try {
        
        const connectionInstance = await mongoose.connect(`mongodb+srv://kartikeysangal:kartikeysangal@cluster0.b5qrd.mongodb.net/yellowpages`)
        console.log(`MongoDB Connected! DB Host: ${connectionInstance.connection.host}`);
        
    } catch (error) {
        console.error("Error connecting to MongoDB:", error);
        process.exit(1);
    }
}

export default connectDB;