public class AccountService {
    public void process(List<Account> accounts) {
        List<Contact> related = [SELECT Id FROM Contact WHERE AccountId = :accounts];
        ContactHelper.touch(related);
    }
}
