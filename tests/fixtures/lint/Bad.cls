public class Bad {
    public void process(List<Account> accounts) {
        for (Account a : accounts) {
            List<Contact> cs = [SELECT Id FROM Contact WHERE AccountId = :a.Id];
            insert cs;
        }
    }
}
