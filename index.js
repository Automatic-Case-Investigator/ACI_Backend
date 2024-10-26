import SOARWrapperBuilder from "./objects/soar-wrapper/soar-wrapper-builder.js";
import { SOARTYPES } from "./constants/soar-types.js";
import selectCharacteristics from "./objects/char-selector/char-selector.js";

async function run() {
    const soar = new SOARWrapperBuilder()
        .setUrl("http://dev-server:9000")
        .setAPIKey("zxUw/VPes33aXLBtXrdgAOTZYQLzZEBE")
        .setSOARType(SOARTYPES.THEHIVE)
        .build();
    const primaryCaseData = selectCharacteristics(await soar.getCase("~4530368"), SOARTYPES.THEHIVE);
    console.log(primaryCaseData.description.replaceAll(/[|*#]/g, ""));
}

run();