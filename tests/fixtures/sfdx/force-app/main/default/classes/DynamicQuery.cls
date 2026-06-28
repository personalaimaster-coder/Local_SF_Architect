public class DynamicQuery {
    public List<SObject> run(String objectName) {
        String soql = 'SELECT Id FROM ' + objectName;
        return Database.query(soql);
    }
}
