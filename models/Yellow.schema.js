
import mongoose from "mongoose";


const yellowSchema = new mongoose.Schema({
    name:{
        type: String,
        required: true
    },
    url: {
        type: String,
        unique: true
    },
    domain: {
        type: String,
        unique: true,
        required:true
    },
    phone: {
        type: String,
        unique: true
    },
    address: {
        type: String
    },
    city: {
        type: String
    }
})

const Yellow = mongoose.model("Yellow", yellowSchema)
export default Yellow;