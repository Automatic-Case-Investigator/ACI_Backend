import { SOARTYPES } from "../../constants/soar-types.js";
import { standardCaseFormat } from "../../constants/standard-case-format.js";


function selectCharsTheHive(data) {
    const formattedData = Object.create(standardCaseFormat);
    formattedData.timestamp = data._createdAt;
    formattedData.title = data.title;
    formattedData.description = data.description;

    return formattedData;
}

export default function selectCharacteristics(data, soarType) {
    switch (soarType) {
        case SOARTYPES.THEHIVE:
            return selectCharsTheHive(data);
    }
}