public with sharing class Clean {
    public void process(List<Account> accounts) {
        List<Contact> cs = [SELECT Id FROM Contact];
        List<Contact> toUpdate = new List<Contact>();
        for (Contact c : cs) {
            toUpdate.add(c);
        }
        update toUpdate;
    }
}
