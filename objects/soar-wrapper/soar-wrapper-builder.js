import { SOARTYPES } from "../../constants/soar-types.js";
import TheHiveWrapper from "./thehive-wrapper.js";

class SOARWrapperBuilder {
    constructor({url: url, apiKey: apiKey, soarType: soarType} = {}) {
        this.url = url;
        this.apiKey = apiKey;
        this.soarType = soarType;
    }
    setUrl(url) {
        this.url = url;
        return this;
    }
    setAPIKey(apiKey) {
        this.apiKey = apiKey;
        return this;
    }
    setSOARType(soarType) {
        this.soarType = soarType;
        return this;
    }
    build() {
        var builderObj = null;
        switch (this.soarType) {
            case SOARTYPES.THEHIVE:
                builderObj = new TheHiveWrapper(this.url, this.apiKey);
                break;
        }
        return builderObj;
    }
}

export default SOARWrapperBuilder;