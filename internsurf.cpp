#include<iostream>
#include<vector>
#include<ctime>

using namespace std;

string getDate() {
    time_t now = time(0);
    tm* localtm = localtime(&now); 

    int year = localtm->tm_year + 1900;
    int month = localtm->tm_mon + 1;
    int day = localtm->tm_mday;

    string date = to_string(month) + "/" + to_string(day) + "/" + to_string(year);
    return date;
}

struct internship {
    enum Status {Applied, Denied, NeedToApply, Interview} status;
    string companyName;
    string date;
    bool connection;

    internship(Status stat, string compname, string dt, bool cnctn) : status(stat), companyName(compname), date(dt), connection(cnctn) {}
};

class internshipSurf {
    public: 

    internshipSurf() = default;
    
    void addInternship(const internship& intship) {
        iList.push_back(intship);
    }

    bool appExists(internship intsh) {
        for (int i = 0; i < iList.size(); i++) {
            if (iList[i].companyName == intsh.companyName) {
                return true;
            }
    }
    return false;
    }

    vector<internship> getInternship() {
        return iList;
    }

    internship search(string company) {
        for (int i = 0; i < iList.size(); i++) {
            if (iList[i].companyName == company) {
                return iList[i];
            }
        }
    }
    

    private:

    vector<internship> iList;

};

int main() {
    int num; 
    cout << "What would you like to do?" << endl;

    cout << "1. Add internship" << endl;
    cout << "2. Search for internship" << endl;
    cout << "3. Change internship status" << endl;
    cout << "4. Display all internships" << endl;



    while (true) {
    cin >> num;


    if (num == 1) {
        string name;
        string date = getDate();
        
        cout << "Name of internship?" << endl;
        
        cin >> name;

        break;
    }

    else if (num == 2) {
        break;
    }

    else if (num == 3) {
        break;
    }
    else if (num == 4) {
        break;
    }

    else {
        cout << "Please type a valid number" << endl;
    }
    }

}