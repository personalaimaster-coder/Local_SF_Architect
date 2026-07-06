public with sharing class BadRules {
    public void run(String userInput) {
        Account a = [SELECT Id FROM Account WHERE Id = '001000000000abcAAA' LIMIT 1];
        String endpoint = 'https://api.example.com/data';
        List<Account> results = Database.query('SELECT Id FROM Account WHERE Name = \'' + userInput + '\'');
        try {
            System.debug('processing');
        } catch (Exception e) {
        }
        for (Integer i = 0; i < 10; i++) {
            if (i > 0) {
                while (i < 5) {
                    if (a != null) {
                        System.debug('deep');
                    }
                }
            }
        }
    }
}
