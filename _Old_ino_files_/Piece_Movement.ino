int stepsPerSquare = 1; //Stepper motor steps per square

//Holds the current state of the board.
//0,1 white garage and 10, 11 black garage
char board[8][12]={ 
{' ', ' ', 'R', 'H', 'B', 'Q', 'K', 'B', 'H', 'R', ' ', ' '},
{' ', ' ', 'P', 'P', 'P', 'P', 'P', 'P', 'P', 'P', ' ', ' '},
{' ', ' ', ' ', ' ', ' ', ' ',' ', ' ', ' ', ' ', ' ', ' '},
{' ', ' ', ' ', ' ', ' ', ' ',' ', ' ', ' ', ' ', ' ', ' '},
{' ', ' ', ' ', ' ', ' ', ' ',' ', ' ', ' ', ' ', ' ', ' '},
{' ', ' ', ' ', ' ', ' ', ' ',' ', ' ', ' ', ' ', ' ', ' '},
{' ', ' ','p', 'p', 'p', 'p', 'p', 'p', 'p', 'p', ' ', ' '},
{' ', ' ', 'r', 'h', 'b', 'k', 'q', 'b', 'h', 'r', ' ', ' '}
};
int * steps = (int*) malloc(2 * sizeof(int)); //I'm not using this right now I think
int * moveArray= (int*) malloc(4 * sizeof(int)); //Represents the start and end position of the move. 0,2 are y cordinates and 1,3 are x cordinates

void setup() {
  Serial.begin(9600);
}
void loop() {
  Serial.println("awaiting input");
  while (Serial.available()==0){}
  String piMove = Serial.readString();
  removeLetters(piMove, moveArray);
}



void removeLetters(String piMove, int * moveArray){
  moveArray[0] = letterToNumber(piMove.charAt(0));
  moveArray[1] = piMove.charAt(1) - '0';
  moveArray[2] = letterToNumber(piMove.charAt(2));
  moveArray[3]= piMove.charAt(3) - '0';
}

int letterToNumber(char letter){ //Converts chess notation to board array values
  if (letter == 'a'){
    return 2;
  }
  if (letter == 'b'){
    return 3;
  }
  if (letter == 'c'){
    return 4;
  }
  if (letter == 'd'){
    return 5;
  }
  if (letter == 'e'){
    return 6;
  }
  if (letter == 'f'){
    return 7;
  }
  if (letter == 'g'){
    return 8;
  }
  if (letter == 'h'){
    return 9;
  }

}

//Gets the current place the piece should be put in the garage
//This method is definently inefficent but idc change if you want to 
int * getGarageLocation(char piece, int * garageLocation){
    garageLocation[1] = -1;
    garageLocation[0] = -1;
    if (piece == 'p'){
      garageLocation[1] = 1;
      for ( int i = 0; i < 7; i++){
          if (board[i][1] == ' '){
            garageLocation[0] = i;
            return garageLocation;
          }
       } 
       garageLocation[0] = 7;
       return garageLocation;
    }
    else if (piece == 'P'){
      garageLocation[1] = 10;
      for ( int i = 0; i < 7; i++){
          if (board[i][10] == ' '){
            garageLocation[0] = i;
            return garageLocation;
          }
       } 
       garageLocation[0] = 7;
       return garageLocation;
    }
    else if (piece == 'r'){
      garageLocation[1] = 0;
      if (board[0][0] == ' '){
        garageLocation[0] = 0;
        return garageLocation;
      }
       garageLocation[0] = 7;
       return garageLocation;
    }
    else if (piece == 'R'){
      garageLocation[1] = 11;
      if (board[0][0] == ' '){
        garageLocation[0] = 0;
        return garageLocation;
      }
       garageLocation[0] = 7;
       return garageLocation;
    }
    else if (piece == 'h'){
      garageLocation[1] = 0;
      if (board[1][0] == ' '){
        garageLocation[0] = 1;
        return garageLocation;
      }
       garageLocation[0] = 6;
       return garageLocation;
    }
    else if (piece == 'H'){
      garageLocation[1] = 11;
      if (board[1][0] == ' '){
        garageLocation[0] = 1;
        return garageLocation;
      }
       garageLocation[0] = 6;
       return garageLocation;
    }
    else if (piece == 'b'){
      garageLocation[1] = 0;
      if (board[2][0] == ' '){
        garageLocation[0] = 2;
        return garageLocation;
      }
       garageLocation[0] = 5;
       return garageLocation;
    }
    else if (piece == 'B'){
      garageLocation[1] = 11;
      if (board[2][0] == ' '){
        garageLocation[0] = 2;
        return garageLocation;
      }
       garageLocation[0] = 5;
       return garageLocation;
    }
    else if (piece == 'q'){
      garageLocation[1] = 0;
      garageLocation[0] = 3;
      return garageLocation;
    }
    else if (piece == 'Q'){
      garageLocation[1] = 11;
      garageLocation[0] = 4;
      return garageLocation;
    }
    else if (piece == 'k'){
      garageLocation[1] = 0;
      garageLocation[0] = 4;
      return garageLocation;
    }
    else if (piece == 'K'){
      garageLocation[1] =11;
      garageLocation[0] = 3;
      return garageLocation;
    }
    return garageLocation;
}

//Check Knight or Garage Movement for blockers
int checkForBlockers(String move){
   int x = move.charAt(1) - move.charAt(3);
   int y = move.charAt(0) - move.charAt(2);
   int blocked = 0;
   for (int i = 1; i <= x; i++){
       if (board[move.charAt(0) - 0][move.charAt(1+i) - 0] != ' '){
          blocked = 1;
       }
   }
   for (int i = 1; i <= y; i++){
       if (board[move.charAt(0+i) - 0][move.charAt(1) - 0] != ' '){
          blocked = 1;
       }
   }
   return blocked;
}

//TODO FIX THIS MESS
void setStepsArray(String move, int * steps){ 
  if (board[move.charAt(2) - 0][move.charAt(3) - 0] != ' '){
     //capture(board[move.charAt(2) - 0][move.charAt(3) - 0]);
  }
  else {
     //find route for piece
  }
}
